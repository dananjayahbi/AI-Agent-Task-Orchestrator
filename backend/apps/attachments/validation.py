"""Upload validation: size, MIME content sniffing, de-duplication (MT-1.11-02).

The endpoint-independent stage that runs **before any bytes are stored**
(Section 9.5 limits and safety; Section 12.1 malicious-upload threat):

* **size caps** — per file (25 MB default), per task count (10) and per
  task total (100 MB); all configurable through the Section 9.10
  ``ATTACHMENT_`` group with the plan defaults (documented defaults —
  the plan fixes the numbers as defaults, the environment may lower or
  raise them);
* **content sniffing, never extension** — magic-byte sniffing against
  the exact Section 9.5 allowlist; the declared multipart type, when
  present, must agree with the sniffed one or the upload is rejected;
* **de-duplication identity** — the sha256 of the bytes: identical
  content maps to one stored object and one attachment record per task
  (Sections 9.5, 16.3; the record-level mapping lives in the upload
  service, this module supplies the digest and the lookup helper).

**Sniffing implementation** (recorded choice, MT-1.11-02 risk note): a
pure-Python magic-byte sniffer, no native library. Each binary format
gets its real signature check; **DOCX is verified structurally** — the
zip container must hold ``word/document.xml`` (an OOXML word-processing
document), not merely zip magic, so renamed zips are refused. Markdown
and plain text have no magic number: they sniff as "text" by strict
UTF-8 decodability with no NUL bytes and no binary control characters;
the two are interchangeable within the text family (a markdown file is
valid plain text and vice versa — the plan lists both in one allowlist).

Rejection codes (Section 20.4 item 5, catalog only): wrong/mismatched
type → ``ATTACHMENT_UNSUPPORTED_FORMAT`` (415); oversize / over-count /
over-total / empty → ``VALIDATION_ERROR`` (400) with structured details.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from typing import Final

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.tasks.models import Task

from .exceptions import AttachmentUnsupportedFormat
from .models import TaskAttachment
from .storage import hash_bytes

# --- the Section 9.5 allowlist, verbatim (none added, none dropped) ---------

DOCX_MIME: Final = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED_MIME_TYPES: Final[tuple[str, ...]] = (
    "image/png",
    "image/jpeg",
    "image/webp",
    "application/pdf",
    DOCX_MIME,
    "text/markdown",
    "text/plain",
)
IMAGE_MIME_TYPES: Final[frozenset[str]] = frozenset({"image/png", "image/jpeg", "image/webp"})
# Markdown and plain text are one sniffable family (no magic number; the
# plan's allowlist lists both). A declared type from this family matches
# a sniffed text and vice versa.
TEXT_MIME_TYPES: Final[frozenset[str]] = frozenset({"text/markdown", "text/plain"})


@dataclass(frozen=True)
class ValidatedUpload:
    """One accepted upload's derived identity (the service's inputs)."""

    filename: str  # client name, path components stripped
    mime_type: str  # the sniffed type — never the declared one
    size_bytes: int
    sha256: str
    is_image: bool


# --- magic-byte sniffing (Section 9.5: content, not extension) --------------

_PNG_MAGIC: Final = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC: Final = b"\xff\xd8\xff"
_WEBP_MAGIC: Final = b"RIFF"
_WEBP_OFFSET: Final = 8  # "RIFF" + 4-byte size, then "WEBP"
_PDF_MAGIC: Final = b"%PDF-"
_ZIP_MAGIC: Final = b"PK\x03\x04"

# Characters allowed in sniffed text: printable, plus the common whitespace
# set. Any other C0 control byte (or a NUL) means binary masquerading as text.
_TEXT_FORBIDDEN_CONTROLS: Final[frozenset[int]] = frozenset(
    byte for byte in range(0x20) if byte not in (0x09, 0x0A, 0x0D, 0x0C, 0x08)
) | {0x7F}


def _looks_like_text(data: bytes) -> bool:
    """Strict UTF-8 text with no NULs and no binary control bytes."""
    if b"\x00" in data:
        return False
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return not any(ord(character) in _TEXT_FORBIDDEN_CONTROLS for character in text)


def _looks_like_docx(data: bytes) -> bool:
    """Zip container **with** a word-processing document part inside.

    MT-1.11-02 risk note made executable: ``application/zip`` magic alone
    never passes DOCX — the container must hold ``word/document.xml`` (an
    OOXML word-processing document). A truncated or non-OOXML zip
    answers "not DOCX"; a corrupt container that raises ``BadZipFile``
    answers "not anything" (treated as unrecognised below).
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


def sniff_mime(data: bytes) -> str | None:
    """The Section 9.5 type for *data*, or ``None`` when unrecognised.

    Binary formats match by signature; DOCX additionally by internal
    structure; the text family by strict decodability. Extension and
    declared type never influence the result.
    """
    if data.startswith(_PNG_MAGIC):
        return "image/png"
    if data.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    if data.startswith(_WEBP_MAGIC) and data[_WEBP_OFFSET : _WEBP_OFFSET + 4] == b"WEBP":
        return "image/webp"
    if data.startswith(_PDF_MAGIC):
        return "application/pdf"
    if data.startswith(_ZIP_MAGIC) and _looks_like_docx(data):
        return DOCX_MIME
    if _looks_like_text(data):
        # The text family's one sniffable shape: markdown and plain text
        # are interchangeable here (module docstring); the declared type
        # refines it in validate_upload.
        return "text/plain"
    return None


def _declared_matches(declared: str, sniffed: str) -> bool:
    """Whether a client-declared type agrees with the sniffed one."""
    if sniffed in TEXT_MIME_TYPES or sniffed == "text/plain":
        return declared in TEXT_MIME_TYPES
    return declared == sniffed


def strip_filename(filename: str) -> str:
    """The client name with every path component removed (Section 12.3).

    Both separators are treated as hostile: ``..\\..\\evil.exe`` and
    ``/etc/passwd`` yield only their final component. The result is
    length-capped at 255 (the model column) — a longer name is trimmed,
    never rejected (the bytes, not the label, are the content).
    """
    base = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return base[:255]


def validate_upload(
    *,
    filename: str,
    declared_mime: str | None,
    data: bytes,
) -> ValidatedUpload:
    """Run the full MT-1.11-02 stage on in-memory *data*; raise on refusal.

    Order matters and is the documented one: **size first** (cheap, and
    an oversize body never gets sniffed), then content sniffing against
    the allowlist, then the declared-vs-sniffed agreement, then the
    non-empty floor. Every rejection raises before any storage call.

    The client-declared type, when present, must agree with the sniffed
    one — with one recorded reading: ``application/octet-stream`` (the
    multipart default a parser assigns to a part that declared no type)
    is treated as *no declaration*, never as a claim to reject on. The
    sniffed content type decides in that case, which is exactly the
    Section 9.5 rule ("content sniffing, not just by extension").
    """
    max_file_bytes = settings.ATTACHMENT_MAX_FILE_BYTES
    if declared_mime == "application/octet-stream":
        declared_mime = None
    size_bytes = len(data)
    if size_bytes == 0:
        raise ValidationError({"file": "The uploaded file is empty."})
    if size_bytes > max_file_bytes:
        raise ValidationError(
            {
                "file": (
                    f"File is {size_bytes} bytes; the per-file limit is "
                    f"{max_file_bytes} bytes (Section 9.5 default, configurable)."
                )
            }
        )

    sniffed = sniff_mime(data)
    if sniffed is None or sniffed not in ALLOWED_MIME_TYPES:
        raise AttachmentUnsupportedFormat(
            "The file content does not match any allowed attachment type "
            "(images, PDF, DOCX, Markdown, plain text — Section 9.5)."
        )
    # A sniffed text file refines to its declared family member when the
    # declaration is a member of the same family (markdown vs plain).
    if sniffed == "text/plain" and declared_mime in TEXT_MIME_TYPES:
        sniffed = declared_mime

    if declared_mime is not None and declared_mime not in ALLOWED_MIME_TYPES:
        raise AttachmentUnsupportedFormat(
            f"Declared type {declared_mime!r} is not in the Section 9.5 allowlist."
        )
    if declared_mime is not None and not _declared_matches(declared_mime, sniffed):
        raise AttachmentUnsupportedFormat(
            f"Declared type {declared_mime!r} contradicts the sniffed content "
            f"type {sniffed!r}; a mismatch is rejected (Section 9.5)."
        )

    clean_name = strip_filename(filename)
    if not clean_name:
        raise ValidationError({"file": "The upload carries no usable filename."})

    return ValidatedUpload(
        filename=clean_name,
        mime_type=sniffed,
        size_bytes=size_bytes,
        sha256=hash_bytes(data),
        is_image=sniffed in IMAGE_MIME_TYPES,
    )


# --- per-task capacity, computed at write time (Section 9.5) -----------------


def check_task_capacity(task: Task, incoming_bytes: int) -> None:
    """Enforce the per-task count and total-size caps for *task*.

    **Call inside the upload transaction, with the task row already
    locked** (``select_for_update`` — the service does that): the MT's
    risk note requires the counters to be atomic at write time or two
    concurrent uploads overshoot the caps. Soft-deleted records
    (MT-1.11-05) no longer consume capacity — their bytes are gone or
    pending retention, so they are excluded from both counters.

    Oversize rejections are ``VALIDATION_ERROR`` with the offending
    numbers in ``details`` (WP-0.5 envelope conventions).
    """
    live = TaskAttachment.objects.filter(task=task, deleted_at__isnull=True)
    max_per_task = settings.ATTACHMENT_MAX_PER_TASK
    max_total_bytes = settings.ATTACHMENT_MAX_TOTAL_BYTES

    count = live.count()
    if count >= max_per_task:
        raise ValidationError(
            {
                "file": (
                    f"Task {task.pk} already has {count} attachments; the "
                    f"per-task limit is {max_per_task} (Section 9.5 default)."
                )
            },
            code="VALIDATION_ERROR",
        )
    total_bytes = sum(size for size in live.values_list("size_bytes", flat=True))
    if total_bytes + incoming_bytes > max_total_bytes:
        raise ValidationError(
            {
                "file": (
                    f"Task {task.pk} attachments total {total_bytes} bytes; "
                    f"{incoming_bytes} more would exceed the {max_total_bytes}-byte "
                    f"per-task total (Section 9.5 default)."
                )
            },
            code="VALIDATION_ERROR",
        )


def existing_attachment_for(task: Task, sha256: str) -> TaskAttachment | None:
    """The task's live attachment with this content, or ``None``.

    The de-duplication probe (Section 9.5): same task + same bytes →
    map to the existing record instead of storing a second copy.
    """
    return (
        TaskAttachment.objects.filter(task=task, sha256=sha256, deleted_at__isnull=True)
        .order_by("created_at")
        .first()
    )


__all__ = [
    "ALLOWED_MIME_TYPES",
    "DOCX_MIME",
    "IMAGE_MIME_TYPES",
    "TEXT_MIME_TYPES",
    "ValidatedUpload",
    "check_task_capacity",
    "existing_attachment_for",
    "sniff_mime",
    "strip_filename",
    "validate_upload",
]
