"""Image stage: normalization, metadata stripping, OCR (Section 9.5 stage 2; MT-1.12-02).

Order is the plan's: normalize resolution (**cap long edge, keep aspect
ratio**), strip metadata (EXIF etc. — on the *derived* copy only; the
stored original is never touched, Section 9.5), run the configured OCR
engine (Section 9.10 / Section 6.6), then ask the description provider
for the layout caption — through WP-1.13's cached provider seam
(:func:`apps.attachments.caption.generate_caption`): the OQ-07 default
provider is **disabled**, so the stage completes OCR-only out of the
box, and the typed provider failure degrades to OCR-only (MT-1.13-05)
instead of failing the stage.

Recorded choices:

* **Output is PNG** for every input type: lossless (OCR quality),
  universally decodable, and written without EXIF/ICC/xmp keys so
  "metadata stripped" is provable by inspecting the saved bytes.
* **EXIF orientation is applied before stripping** — otherwise a phone
  photo would lose both its pixels' orientation tag *and* its rotation.
* **Pixel ceiling** before load (Section 12.1 in-process limits): a
  header claiming > 50 megapixels fails the stage with a human-readable
  reason instead of allocating hundreds of megabytes in the worker.
"""

from __future__ import annotations

import io
import logging
import time
from typing import Final

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

from .caption import generate_caption
from .chunking import ExtractionResult
from .derived import NORMALIZED_IMAGE_NAME, put_derived
from .description import DescriptionProviderError
from .errors import PermanentPipelineError, TransientPipelineError
from .models import TaskAttachment
from .ocr import get_ocr_engine

logger = logging.getLogger(__name__)

#: In-process pixel ceiling for one image (Section 12.1 — documented
#: default, MT-1.12-02/03 risk notes record the sandbox assumption).
MAX_IMAGE_PIXELS: Final = 50_000_000

#: Resampling filter for the down-scale (documented choice: Lanczos).
_RESAMPLE = Image.Resampling.LANCZOS


def normalize_image(data: bytes, *, max_edge: int) -> bytes:
    """Return *data* re-encoded as PNG: long edge ≤ *max_edge*, aspect
    ratio preserved, every metadata block gone (Section 9.5).

    Raises :class:`PermanentPipelineError` for undecodable or
    over-ceiling input — deterministic content problems, never retried.
    """
    try:
        source = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError) as exc:
        raise PermanentPipelineError(
            "the stored bytes are not a decodable image (permanent content failure)"
        ) from exc

    width, height = source.size
    if width * height > MAX_IMAGE_PIXELS:
        raise PermanentPipelineError(
            f"image declares {width * height} pixels, above the "
            f"{MAX_IMAGE_PIXELS}-pixel processing ceiling (Section 12.1 limit)"
        )
    try:
        source.load()
    except OSError as exc:
        raise PermanentPipelineError(
            "the stored image is truncated or corrupt (permanent content failure)"
        ) from exc

    # Orientation first (so stripping EXIF loses nothing), then cap the
    # long edge proportionally — aspect ratio preserved by construction.
    image = ImageOps.exif_transpose(source)
    if image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
        image = image.convert("RGB")
    width, height = image.size
    long_edge = max(width, height)
    if long_edge > max_edge:
        scale = max_edge / long_edge
        image = image.resize(
            (max(1, round(width * scale)), max(1, round(height * scale))),
            _RESAMPLE,
        )

    buffer = io.BytesIO()
    # No exif=/icc_profile=/pnginfo kwargs: the encoder then writes a
    # metadata-free file — the stripping proof the tests assert.
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def process_image(attachment: TaskAttachment, data: bytes, *, deadline: float) -> ExtractionResult:
    """Normalize → strip → OCR → caption for one image attachment.

    Persists ``ocr_text`` and ``layout_caption`` on the record, stores
    the normalized PNG as derived data, and returns the transcript as a
    single page (the page-oriented path of MT-1.12-05).
    """
    if time.monotonic() > deadline:
        raise TransientPipelineError(
            "attachment processing exceeded the parse time budget (transient)"
        )
    normalized = normalize_image(data, max_edge=settings.ATTACHMENT_IMAGE_MAX_EDGE_PX)
    put_derived(str(attachment.pk), NORMALIZED_IMAGE_NAME, normalized)

    transcript = get_ocr_engine().recognize(normalized, mime_type="image/png")

    # Section 9.5: failures degrade to OCR-only (never fail the stage).
    # Only the *typed* provider failure degrades (MT-1.13-05): a
    # programming error must surface instead of becoming an invisible
    # "successful" run. The cache (MT-1.13-04) lives in generate_caption.
    try:
        caption = generate_caption(attachment, image_png=normalized, ocr_text=transcript)
    except DescriptionProviderError as exc:
        logger.warning(
            "description provider failed; degrading to OCR-only (transient=%s, reason=%s)",
            exc.transient,
            exc.reason,
        )
        caption = ""

    attachment.ocr_text = transcript
    attachment.layout_caption = caption
    attachment.save(update_fields=["ocr_text", "layout_caption"])
    return ExtractionResult(pages=(transcript,))


__all__ = [
    "MAX_IMAGE_PIXELS",
    "normalize_image",
    "process_image",
]
