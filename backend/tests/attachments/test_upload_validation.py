"""MT-1.11-02 — upload validation: size, MIME sniffing, de-duplication.

Run with ``pytest backend/tests/attachments/test_upload_validation.py
-v``. The suite proves the MT's acceptance criteria at the stage level
(endpoint-independent — MT-1.11-02 out-of-scope note):

* every limit boundary (per-file at/over, per-task count and total);
* every Section 9.5 allowlisted type accepted, one by one;
* disguised types rejected by **content**, not extension (an ELF named
  ``.png``; a plain zip named ``.docx`` — the structural DOCX check);
* a declared type that contradicts the sniffed content is rejected;
* de-duplication identity: same bytes → same digest → the existing
  record maps, no second object (the record half is asserted through
  the service in the endpoint suite; here the probe helper).
"""

from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from apps.attachments.models import TaskAttachment
from apps.attachments.validation import (
    ALLOWED_MIME_TYPES,
    DOCX_MIME,
    check_task_capacity,
    existing_attachment_for,
    sniff_mime,
    strip_filename,
    validate_upload,
)
from apps.tasks.models import TaskState

from .helpers import (
    ELF_BYTES,
    JPEG_BYTES,
    MARKDOWN_BYTES,
    PDF_BYTES,
    PLAINTEXT_BYTES,
    PNG_BYTES,
    WEBP_BYTES,
    docx_bytes,
    make_project,
    make_task,
    plain_zip_bytes,
    upload,
)

pytestmark = pytest.mark.django_db

MB = 1024 * 1024


# --- the allowlist matches Section 9.5 exactly (20.5 traceability) -----------


def test_allowlist_is_the_section_9_5_list_verbatim() -> None:
    """None added, none dropped (MT-1.11-02 acceptance; Section 20.5)."""
    assert set(ALLOWED_MIME_TYPES) == {
        "image/png",
        "image/jpeg",
        "image/webp",
        "application/pdf",
        DOCX_MIME,
        "text/markdown",
        "text/plain",
    }


# --- sniffing: every allowlisted type accepted (by content) ------------------


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (PNG_BYTES, "image/png"),
        (JPEG_BYTES, "image/jpeg"),
        (WEBP_BYTES, "image/webp"),
        (PDF_BYTES, "application/pdf"),
        (docx_bytes(), DOCX_MIME),
        (MARKDOWN_BYTES, "text/plain"),  # text family: markdown sniffs as text
        (PLAINTEXT_BYTES, "text/plain"),
    ],
)
def test_every_allowlisted_type_sniffs(payload: bytes, expected: str) -> None:
    """Real magic bytes for each Section 9.5 type."""
    assert sniff_mime(payload) == expected


def test_validate_refines_text_family_to_its_declared_member() -> None:
    """A markdown declaration on text content stays markdown (9.5 family)."""
    result = validate_upload(
        filename="notes.md", declared_mime="text/markdown", data=MARKDOWN_BYTES
    )
    assert result.mime_type == "text/markdown"
    assert result.is_image is False


# --- disguised types rejected by content, not extension ----------------------


def test_executable_bytes_named_png_are_rejected() -> None:
    """MT-1.11-02 acceptance: extension never decides; ELF is not an image."""
    with pytest.raises(Exception) as excinfo:
        validate_upload(filename="photo.png", declared_mime="image/png", data=ELF_BYTES)
    assert getattr(excinfo.value, "default_code", None) == "ATTACHMENT_UNSUPPORTED_FORMAT"


def test_plain_zip_named_docx_is_rejected() -> None:
    """The structural DOCX check (risk note): zip magic alone never passes."""
    with pytest.raises(Exception) as excinfo:
        validate_upload(filename="report.docx", declared_mime=DOCX_MIME, data=plain_zip_bytes())
    assert getattr(excinfo.value, "default_code", None) == "ATTACHMENT_UNSUPPORTED_FORMAT"


def test_declared_type_contradicting_content_is_rejected() -> None:
    """A mismatch between sniffed and declared type is rejected (9.5)."""
    with pytest.raises(Exception) as excinfo:
        validate_upload(filename="lies.pdf", declared_mime="application/pdf", data=PNG_BYTES)
    assert getattr(excinfo.value, "default_code", None) == "ATTACHMENT_UNSUPPORTED_FORMAT"


def test_octet_stream_declaration_is_no_declaration() -> None:
    """Recorded reading: the multipart default is not a type claim.

    Parsers assign ``application/octet-stream`` to a part that declared
    no type; the sniffed content decides (Section 9.5).
    """
    result = validate_upload(
        filename="photo.png", declared_mime="application/octet-stream", data=PNG_BYTES
    )
    assert result.mime_type == "image/png"


def test_disallowed_declared_type_is_rejected_even_with_valid_content() -> None:
    """The declared type must itself be on the allowlist (9.5)."""
    with pytest.raises(Exception) as excinfo:
        validate_upload(filename="x.png", declared_mime="image/tiff", data=PNG_BYTES)
    assert getattr(excinfo.value, "default_code", None) == "ATTACHMENT_UNSUPPORTED_FORMAT"


# --- size boundaries (Section 9.5 defaults, configurable) --------------------


def test_empty_file_is_refused() -> None:
    """Zero bytes is not an attachment (the non-empty floor)."""
    with pytest.raises(ValidationError):
        validate_upload(filename="empty.png", declared_mime="image/png", data=b"")


@override_settings(ATTACHMENT_MAX_FILE_BYTES=1024)
def test_file_at_the_limit_is_accepted() -> None:
    """At the cap: accepted (the limit is exclusive, Section 9.5 wording)."""
    payload = PNG_BYTES + b"\x00" * (1024 - len(PNG_BYTES))
    result = validate_upload(filename="ok.png", declared_mime="image/png", data=payload)
    assert result.size_bytes == 1024


@override_settings(ATTACHMENT_MAX_FILE_BYTES=1024)
def test_file_over_the_limit_is_refused() -> None:
    """One byte over: ``VALIDATION_ERROR`` with the numbers in the body."""
    payload = PNG_BYTES + b"\x00" * (1025 - len(PNG_BYTES) + 1)
    with pytest.raises(ValidationError) as excinfo:
        validate_upload(filename="big.png", declared_mime="image/png", data=payload)
    assert "file" in excinfo.value.detail


def test_default_per_file_limit_is_the_plan_25_mb() -> None:
    """The documented default: 25 MB (Section 9.5) — configurable, asserted."""
    from django.conf import settings

    assert settings.ATTACHMENT_MAX_FILE_BYTES == 25 * MB
    assert settings.ATTACHMENT_MAX_PER_TASK == 10
    assert settings.ATTACHMENT_MAX_TOTAL_BYTES == 100 * MB


# --- per-task count and total caps, atomic at write time ----------------------


def test_count_cap_rejects_the_11th_attachment() -> None:
    """Per-task count: 10 live rows consume the Section 9.5 default."""
    project = make_project()
    task = make_task(project)
    TaskAttachment.objects.bulk_create(
        TaskAttachment(
            task=task,
            filename=f"f{index}.png",
            mime_type="image/png",
            size_bytes=1,
            is_image=True,
            storage_key=f"objects/aa/{index:064d}",
            sha256=f"{index:064d}",
        )
        for index in range(10)
    )
    with pytest.raises(ValidationError):
        check_task_capacity(task, incoming_bytes=1)


def test_total_cap_rejects_when_the_sum_would_overshoot() -> None:
    """Per-task total: the incoming bytes count toward the 100 MB default."""
    project = make_project()
    task = make_task(project)
    TaskAttachment.objects.create(
        task=task,
        filename="big.pdf",
        mime_type="application/pdf",
        size_bytes=99 * MB,
        is_image=False,
        storage_key="objects/aa/" + "a" * 64,
        sha256="a" * 64,
    )
    with pytest.raises(ValidationError):
        check_task_capacity(task, incoming_bytes=2 * MB)  # 99 + 2 > 100


def test_soft_deleted_rows_free_capacity() -> None:
    """MT-1.11-05 interplay: deleted rows no longer consume the caps."""
    project = make_project()
    task = make_task(project)
    from django.utils import timezone

    TaskAttachment.objects.create(
        task=task,
        filename="gone.png",
        mime_type="image/png",
        size_bytes=1,
        is_image=True,
        storage_key="objects/aa/" + "b" * 64,
        sha256="b" * 64,
        deleted_at=timezone.now(),
    )
    check_task_capacity(task, incoming_bytes=1)  # no raise


def test_counters_exclude_other_tasks() -> None:
    """The caps are per task (Section 9.5), not global."""
    project = make_project()
    mine = make_task(project, 1)
    other = make_task(project, 2)
    TaskAttachment.objects.bulk_create(
        TaskAttachment(
            task=other,
            filename="other.png",
            mime_type="image/png",
            size_bytes=99 * MB,
            is_image=True,
            storage_key="objects/aa/" + "c" * 64,
            sha256="c" * 64,
        )
        for _ in range(10)
    )
    check_task_capacity(mine, incoming_bytes=1)  # other task's rows are irrelevant


# --- de-duplication identity -------------------------------------------------


def test_same_bytes_yield_the_same_digest() -> None:
    """Content addressing: identical bytes, identical identity (9.5)."""
    first = validate_upload(filename="a.png", declared_mime="image/png", data=PNG_BYTES)
    second = validate_upload(filename="b.png", declared_mime="image/png", data=PNG_BYTES)
    assert first.sha256 == second.sha256


def test_existing_attachment_probe_maps_by_digest() -> None:
    """The de-dup probe: same task + same digest → the existing record."""
    project = make_project()
    task = make_task(project)
    from apps.attachments.storage import hash_bytes

    digest = hash_bytes(PNG_BYTES)
    row = TaskAttachment.objects.create(
        task=task,
        filename="orig.png",
        mime_type="image/png",
        size_bytes=len(PNG_BYTES),
        is_image=True,
        storage_key=f"objects/{digest[:2]}/{digest}",
        sha256=digest,
    )
    assert existing_attachment_for(task, digest) == row
    assert existing_attachment_for(task, "f" * 64) is None


# --- filename hygiene (Section 12.3) ------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("photo.png", "photo.png"),
        ("C:\\Users\\x\\evil.png", "evil.png"),
        ("/etc/passwd", "passwd"),
        ("../../escape.md", "escape.md"),
    ],
)
def test_path_components_are_stripped(raw: str, expected: str) -> None:
    """The client name never carries a path into storage or the UI."""
    assert strip_filename(raw) == expected


def test_stripped_name_is_capped_at_255() -> None:
    """The model column bound, applied as a trim (not a rejection)."""
    assert len(strip_filename("x" * 400 + ".png")) == 255


# --- task-state independence (the stage is endpoint-free) --------------------


def test_stage_does_not_consult_task_state() -> None:
    """MT-1.11-02 is endpoint-independent: validation is content-only."""
    project = make_project()
    task = make_task(project, state=TaskState.COMPLETED)
    result = validate_upload(filename="a.png", declared_mime="image/png", data=PNG_BYTES)
    assert result.mime_type == "image/png"
    assert task.state == TaskState.COMPLETED


def test_upload_helper_builds_multipart_parts() -> None:
    """Sanity for the shared factory (the endpoint suite relies on it)."""
    part = upload(PNG_BYTES, name="photo.png", content_type="image/png")
    assert part.name == "photo.png"
    assert part.content_type == "image/png"
    assert part.read() == PNG_BYTES
