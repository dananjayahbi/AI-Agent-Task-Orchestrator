"""PDF stage: embedded text layer first, OCR fallback for scanned pages
(Section 9.5 documents stage; Sections 12.1, 19.1; MT-1.12-03).

Per-page rules (the plan's order made precise):

1. **Text layer first** — a page whose layer yields any non-whitespace
   character is served from the text; OCR is *not* invoked for it (cost
   control: "do not silently OCR every page").
2. **OCR fallback** — a page with an *empty* layer is treated as
   scanned/image-only; its embedded images are extracted and run
   through the shared MT-1.12-02 engine. The documented threshold is
   **strictly empty text** (a one-character layer wins over OCR —
   misclassification toward the text layer is deterministic and cheap;
   MT-1.12-03 risk note: record the threshold, don't hide it).
3. **Page boundaries are preserved** — one string per page flows into
   MT-1.12-05's page-oriented path, so ``page_number``/``total_pages``
   stay derivable (Section 19 acceptance: large PDF → numbered pages).

**Worker safety** (Section 12.1 "sandboxed parsing in the worker"; the
MT risk note allows the strongest in-process limits for v1, recording
the assumption): page-count and output-size ceilings, a cooperative
parse-time budget checked between pages, and *every* parser exception
converted into a human-readable permanent failure — a malformed or
hostile PDF fails the stage, never the worker. OS-level sandboxing is
the plan's post-v1 "Could" (Section 12.3), not silently assumed here.
"""

from __future__ import annotations

import io
import logging
import time
from typing import Any, Final

from PIL import Image
from pypdf import PdfReader

from .chunking import ExtractionResult
from .errors import PermanentPipelineError, TransientPipelineError
from .models import TaskAttachment
from .ocr import get_ocr_engine

logger = logging.getLogger(__name__)

#: In-process ceilings (Section 12.1 documented defaults — MT-1.12-03
#: risk note: recorded as choices, not plan facts).
MAX_PDF_PAGES: Final = 2000
MAX_EXTRACTED_CHARS: Final = 5_000_000

#: How the pages are persisted in ``extracted_markdown`` (form feed is
#: the conventional page separator; WP-1.14 paginates on it).
PAGE_SEPARATOR: Final = "\f"


def _open_reader(data: bytes) -> PdfReader:
    """Parse the container, mapping every parser failure to a reason."""
    if not data:
        raise PermanentPipelineError("the stored PDF object is empty")
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise PermanentPipelineError(
                "the PDF is password-protected; decryption is not supported"
            )
        _ = len(reader.pages)  # forces the trailer/page-tree parse now
    except PermanentPipelineError:
        raise
    except Exception as exc:  # hostile input surface: never crash the worker
        raise PermanentPipelineError(f"the PDF could not be parsed ({type(exc).__name__})") from exc
    if len(reader.pages) == 0:
        raise PermanentPipelineError("the PDF contains no pages")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise PermanentPipelineError(
            f"the PDF has {len(reader.pages)} pages, above the "
            f"{MAX_PDF_PAGES}-page processing ceiling (Section 12.1 limit)"
        )
    return reader


def _page_text(page: Any) -> str:
    """One page's embedded text layer (``""`` when absent)."""
    try:
        return page.extract_text() or ""
    except Exception as exc:  # malformed content surface
        raise PermanentPipelineError(
            f"the PDF text layer could not be read ({type(exc).__name__})"
        ) from exc


def _page_as_png(image_file: Any) -> bytes:
    """Re-encode one embedded page image as PNG for the OCR engine."""
    try:
        image = image_file.image  # pypdf's PIL accessor (needs Pillow)
        if not isinstance(image, Image.Image):  # defensive: engine contract
            raise TypeError("pypdf returned a non-PIL image")
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as exc:  # embedded image surface
        raise PermanentPipelineError(
            f"a scanned page image could not be decoded ({type(exc).__name__})"
        ) from exc


def process_pdf(attachment: TaskAttachment, data: bytes, *, deadline: float) -> ExtractionResult:
    """Extract every page of *data* — text layer, OCR only where empty.

    Persists ``extracted_markdown`` (pages joined by a form feed) and
    returns the per-page tuple for chunking. OCR runs lazily: a
    text-layer PDF never touches the engine (MT-1.12-03 acceptance).
    """
    reader = _open_reader(data)
    engine = None  # constructed only if a scanned page appears
    pages: list[str] = []
    total_chars = 0

    for page_number, page in enumerate(reader.pages, start=1):
        if time.monotonic() > deadline:
            raise TransientPipelineError(
                "PDF parsing exceeded the parse time budget (transient; "
                "retried with backoff — Section 9.9)"
            )
        text = _page_text(page)
        if not text.strip():
            # Scanned/image-only page → OCR fallback, images only.
            try:
                embedded = list(page.images)
            except Exception as exc:  # noqa: BLE001 - hostile input surface
                raise PermanentPipelineError(
                    f"page {page_number}: scanned images could not be read ({type(exc).__name__})"
                ) from exc
            if not embedded:
                raise PermanentPipelineError(
                    f"page {page_number} has no text layer and no extractable "
                    "image to OCR (unsupported page composition)"
                )
            if engine is None:
                engine = get_ocr_engine()
            transcripts = [
                engine.recognize(_page_as_png(item), mime_type="image/png") for item in embedded
            ]
            text = "\n".join(part for part in transcripts if part)
        pages.append(text)
        total_chars += len(text)
        if total_chars > MAX_EXTRACTED_CHARS:
            raise PermanentPipelineError(
                f"extracted text exceeds the {MAX_EXTRACTED_CHARS}-character "
                "processing ceiling (Section 12.1 limit)"
            )

    attachment.extracted_markdown = PAGE_SEPARATOR.join(pages)
    attachment.save(update_fields=["extracted_markdown"])
    return ExtractionResult(pages=tuple(pages))


__all__ = [
    "MAX_EXTRACTED_CHARS",
    "MAX_PDF_PAGES",
    "PAGE_SEPARATOR",
    "process_pdf",
]
