"""Format resolution and page assembly for the content endpoint
(Section 9.5 retrieval table; Section 9.2; Section 10.4; FR-ATT-04;
MT-1.14-02/03).

One pure module between the view and the stored derived data, so the
Section 9.5 table is testable without HTTP:

* :func:`resolve_format` — the retrieval table's behavior contract for
  the four ``format_preference`` values (WP-1.14 acceptance: "all four
  format preferences behave per table in Section 9.5"). ``auto``
  resolves by attachment type with the **text-safe default** of
  Section 10.4 step 4: documents → ``markdown`` (paginated), images →
  ``text_ocr`` (OCR plus description). Capability-dependent behavior
  beyond that (vision sessions requesting the image block) is the
  bridge's resolver (WP-2.5) passing an explicit format — the REST
  endpoint serves explicit requests as-is (recorded in the changelog).
* :func:`content_page` — the paginated markdown page or the
  non-paginated text/image payload (Section 9.5 pagination clause:
  ``page_number``, ``total_pages`` and the page's token count; the
  recorded one-based, ``total_pages = 1`` for single-page documents
  convention).

Pagination mechanics (MT-1.14-03, the pagination.md content
exception): page-oriented extractions (PDFs — ``page_count`` set)
page by **document page** (that page's chunks joined); token-bounded
extractions (DOCX/Markdown/plain — ``page_number`` null on chunks) use
each chunk **as** the page, so "one page or chunk per call" holds for
both shapes. Out-of-range and non-integer pages are the view's
``VALIDATION_ERROR``; this module raises nothing HTTP-shaped.

**Sensitive content** (Section 12.4): chunk texts and transcripts are
attachment content — this module never logs them.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Final

from .derived import NORMALIZED_IMAGE_NAME
from .models import AttachmentChunk, TaskAttachment
from .storage import derived_key, get_storage

PDF_MIME: Final = "application/pdf"

#: The four Section 9.5 ``format_preference`` values — exactly these.
FORMAT_AUTO: Final = "auto"
FORMAT_IMAGE_BASE64: Final = "image_base64"
FORMAT_TEXT_OCR: Final = "text_ocr"
FORMAT_MARKDOWN: Final = "markdown"
FORMAT_CHOICES: Final[tuple[str, ...]] = (
    FORMAT_AUTO,
    FORMAT_IMAGE_BASE64,
    FORMAT_TEXT_OCR,
    FORMAT_MARKDOWN,
)

#: The normalized image is always PNG (MT-1.12-02's recorded output).
NORMALIZED_MEDIA_TYPE: Final = "image/png"

#: Page text join for a document page split across chunks (documented
#: choice: the chunker's own blank-line separator).
PAGE_JOIN: Final = "\n\n"


class UnsupportedFormatCombination(ValueError):
    """A valid format preference the attachment's type cannot satisfy.

    Carries the human-readable reason; the view maps it to the catalog
    ``ATTACHMENT_UNSUPPORTED_FORMAT`` (Section 9.5 table; Section 20.4
    item 5 — no new code).
    """


@dataclass(frozen=True)
class ContentPage:
    """One delivered content unit — the response's data half.

    ``format`` is the **resolved** concrete format (``auto`` never
    reaches the wire). Exactly one of the content shapes is populated:
    ``image_base64`` + ``media_type`` for images, else ``content``
    (plus ``description`` for ``text_ocr``). Page metadata is ``None``
    for non-paginated formats — never fabricated (MT-1.14-03).
    """

    format: str
    content: str | None = None
    description: str | None = None
    image_base64: str | None = None
    media_type: str | None = None
    page_number: int | None = None
    total_pages: int | None = None
    token_count: int | None = None


def resolve_format(attachment: TaskAttachment, requested: str) -> str:
    """The concrete format for *attachment* under the Section 9.5 table.

    ``auto`` resolves by type (text-safe default, Section 10.4 step 4);
    explicit preferences that the type cannot satisfy raise
    :class:`UnsupportedFormatCombination` — ``image_base64`` on a
    non-image (the table's wording), ``markdown`` on an image, and
    ``text_ocr`` on types the pipeline never OCRs (DOCX/Markdown/plain
    have no OCR representation).
    """
    if requested == FORMAT_AUTO:
        return FORMAT_MARKDOWN if not attachment.is_image else FORMAT_TEXT_OCR
    if requested == FORMAT_IMAGE_BASE64:
        if not attachment.is_image:
            raise UnsupportedFormatCombination(
                "image_base64 serves only image attachments (Section 9.5 "
                "retrieval table); request text_ocr or markdown instead."
            )
        return requested
    if requested == FORMAT_TEXT_OCR:
        if attachment.is_image or attachment.mime_type == PDF_MIME:
            return requested
        raise UnsupportedFormatCombination(
            "text_ocr serves images and PDFs (the OCR-able pipeline "
            "types); this attachment has no OCR representation."
        )
    if requested == FORMAT_MARKDOWN:
        if attachment.is_image:
            raise UnsupportedFormatCombination(
                "markdown serves documents, not images (Section 9.5 "
                "retrieval table); request image_base64 or text_ocr instead."
            )
        return requested
    raise UnsupportedFormatCombination(f"unknown format preference {requested!r}")


def _chunks_for_page(attachment: TaskAttachment, page_number: int) -> list[AttachmentChunk]:
    return list(attachment.chunks.filter(page_number=page_number).order_by("sequence"))


def _document_pages(attachment: TaskAttachment) -> tuple[list[str], list[int]]:
    """(page texts, per-page token counts) in page order.

    Page-oriented extractions page by document page (chunks joined —
    a page longer than the chunk bound reassembles here); token-bounded
    extrations treat each chunk as one page. A processed document with
    no text at all still yields exactly one empty page
    (``total_pages = 1`` — MT-1.14-03).
    """
    if attachment.page_count is not None:
        texts: list[str] = []
        tokens: list[int] = []
        for number in range(1, attachment.page_count + 1):
            chunks = _chunks_for_page(attachment, number)
            texts.append(PAGE_JOIN.join(chunk.text for chunk in chunks))
            tokens.append(sum(chunk.token_estimate for chunk in chunks))
        if not texts:  # defensive: page_count 0 lands here
            return [""], [0]
        return texts, tokens

    chunks = list(attachment.chunks.order_by("sequence"))
    if not chunks:
        return [""], [0]
    return [chunk.text for chunk in chunks], [chunk.token_estimate for chunk in chunks]


def markdown_page(attachment: TaskAttachment, page: int) -> ContentPage:
    """The *page*-th extracted markdown unit with its Section 9.5 metadata.

    One-based; ``page`` outside ``1..total_pages`` raises
    :class:`IndexError` (the view answers ``VALIDATION_ERROR`` — the
    catalog has no page-not-found code, MT-1.14-03).
    """
    texts, tokens = _document_pages(attachment)
    total = len(texts)
    if page < 1 or page > total:
        raise IndexError(f"page {page} outside 1..{total}")
    return ContentPage(
        format=FORMAT_MARKDOWN,
        content=texts[page - 1],
        page_number=page,
        total_pages=total,
        token_count=tokens[page - 1],
    )


def text_ocr_page(attachment: TaskAttachment) -> ContentPage:
    """The transcript plus layout description — non-paginated (single unit).

    A legitimately absent description (OCR-only degradation,
    MT-1.13-05) yields an empty string; the view omits the banner for
    it (nothing delivered).
    """
    return ContentPage(
        format=FORMAT_TEXT_OCR,
        content=attachment.ocr_text,
        description=attachment.layout_caption,
    )


def image_page(attachment: TaskAttachment) -> ContentPage:
    """The Section 9.5 stage-2 normalized image, base64-encoded.

    A missing derived file on a ``ready`` image is a server-side
    integrity fault (the pipeline always writes it) — the raw
    :class:`KeyError` propagates to the envelope handler's logged 500
    (SERVER_ERROR), never a client error (recorded in the changelog).
    """
    data = get_storage().get(derived_key(str(attachment.pk), NORMALIZED_IMAGE_NAME))
    return ContentPage(
        format=FORMAT_IMAGE_BASE64,
        image_base64=base64.b64encode(data).decode("ascii"),
        media_type=NORMALIZED_MEDIA_TYPE,
    )


def content_page(attachment: TaskAttachment, *, resolved: str, page: int) -> ContentPage:
    """The delivered unit for a resolved format (banner applied by the view)."""
    if resolved == FORMAT_MARKDOWN:
        return markdown_page(attachment, page)
    if resolved == FORMAT_TEXT_OCR:
        return text_ocr_page(attachment)
    return image_page(attachment)


__all__ = [
    "FORMAT_AUTO",
    "FORMAT_CHOICES",
    "FORMAT_IMAGE_BASE64",
    "FORMAT_MARKDOWN",
    "FORMAT_TEXT_OCR",
    "ContentPage",
    "UnsupportedFormatCombination",
    "content_page",
    "image_page",
    "markdown_page",
    "resolve_format",
    "text_ocr_page",
]
