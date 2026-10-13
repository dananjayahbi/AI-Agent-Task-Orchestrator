"""Permanent per-attachment description caching (G-14; Section 9.5;
MT-1.13-04).

Two plan sentences fix the requirement. Section 9.5: *"Descriptions are
generated once and cached."* G-14: *"result cached permanently per
attachment (WP-1.13)."* Caching is the cost control that keeps a vision
model from being called on every reprocessing or retry: the description
is a per-attachment, generate-once artifact.

Recorded readings (MT-1.13-04 risk notes):

* **Storage** — the caption lives on the attachment record's
  ``layout_caption`` column (Section 7.2 derived-data field; WP-1.11
  created it with the model, so **no migration is needed** — the MT's
  "isolated migration" target is satisfied by the field's existence).
  Keyed per attachment (G-14: per attachment, not per content hash);
  attachment deletion removes it with the record (derived-but-cached —
  nothing else invalidates it; "permanently" means no TTL, no eviction
  path exists).
* **Read-through** — a stored caption short-circuits the provider: no
  cost, no failure risk. This is what makes "produced once" testable
  across pipeline retries and explicit reprocessing.
* **Write-once** — a successful generation is persisted through a
  compare-and-set (``filter(layout_caption="")`` → ``update``), so two
  concurrent caption attempts can both *call* the provider (documented
  residual race — single-flight would need a lock; MT risk note) but
  only one write wins and the loser adopts the stored value.
* **Failures are never cached** — this module only stores what the
  provider returned; a :class:`~apps.attachments.description.
  DescriptionProviderError` propagates untouched for the pipeline's
  degradation catch (MT-1.13-05), leaving the cache empty so a later
  healthy run still generates.
* **"No description" is not a cached value** — the disabled provider's
  ``""`` (and any empty caption) stores nothing (G-14 caches
  descriptions, not absence): enabling the provider later generates
  normally for such attachments.
"""

from __future__ import annotations

from .description import get_description_provider
from .models import TaskAttachment


def generate_caption(attachment: TaskAttachment, *, image_png: bytes, ocr_text: str) -> str:
    """The attachment's layout caption, generating it at most once (G-14).

    Cache hit → stored text, zero provider calls. Miss → the configured
    provider's caption; a non-empty result is persisted write-once and
    returned. Empty results (disabled provider, empty model output)
    return ``""`` without touching the store. Raises
    :class:`~apps.attachments.description.DescriptionProviderError`
    for provider failures — nothing is stored (MT-1.13-05 consumes it).
    """
    if attachment.layout_caption:
        return attachment.layout_caption

    caption = get_description_provider().describe(
        attachment_id=str(attachment.pk),
        image_png=image_png,
        ocr_text=ocr_text,
    )
    if not caption:
        return ""  # "no description" is never a cached value (G-14)

    written = TaskAttachment.objects.filter(pk=attachment.pk, layout_caption="").update(
        layout_caption=caption
    )
    if written:
        attachment.layout_caption = caption
        return caption
    # A concurrent attempt won the write-once CAS: adopt its value so
    # every caller of this run reports the stored caption.
    attachment.refresh_from_db(fields=["layout_caption"])
    return attachment.layout_caption


__all__ = ["generate_caption"]
