"""Content-endpoint contracts — Section 9.2 retrieval row (WP-1.14).

* ``AttachmentContentQuerySerializer`` — the Section 9.2 ``format`` and
  ``page`` parameters, strictly validated: an unknown ``format`` value
  or non-integer/out-of-range ``page`` is ``VALIDATION_ERROR``, and the
  strict mixin rejects unknown query parameters (MT-0.5-04 discipline;
  MT-1.14-03). ``format`` defaults to ``auto``; ``page`` to 1.
* ``AttachmentContentSerializer`` — the 200 body: the resolved format
  plus exactly the Section 9.5 return fields (``page_number``,
  ``total_pages``, token count on paginated responses) and the
  banner-prefixed text values (P10, MT-1.14-04). Nullable members
  document the asymmetry: non-paginated formats omit page metadata,
  text formats carry no ``image_base64`` and vice versa (no fabricated
  fields, MT-1.14-03).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.serializers import StrictSerializerMixin

from .retrieval import FORMAT_AUTO, FORMAT_CHOICES


class AttachmentContentQuerySerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """``GET /attachments/{id}/content`` query parameters (Section 9.2)."""

    format = serializers.ChoiceField(
        choices=FORMAT_CHOICES,
        required=False,
        default=FORMAT_AUTO,
        help_text=(
            "Section 9.5 retrieval table: auto (default; text-safe — "
            "documents resolve to markdown, images to text_ocr), "
            "image_base64, text_ocr, markdown. Unknown values answer "
            "VALIDATION_ERROR."
        ),
    )
    page = serializers.IntegerField(
        required=False,
        min_value=1,
        default=1,
        help_text=(
            "One-based page for paginated formats (markdown; auto on "
            "documents — Section 9.5 pagination clause, the pagination.md "
            "content exception). Defaults to 1; out-of-range and "
            "non-integer values answer VALIDATION_ERROR. Ignored by the "
            "non-paginated formats."
        ),
    )


class AttachmentContentSerializer(serializers.Serializer[Any]):
    """The content endpoint's 200 body (Section 9.5 retrieval behavior)."""

    attachment_id = serializers.UUIDField(help_text="The addressed attachment (Section 7.2).")
    format = serializers.CharField(
        help_text="The resolved concrete format — `auto` never reaches the wire."
    )
    content = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        help_text=(
            "The delivered text (markdown page or OCR transcript), "
            "prefixed with the untrusted-content banner (P10; Section "
            "9.5). Null for image_base64."
        ),
    )
    description = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        help_text=(
            "text_ocr only: the layout description, banner-prefixed "
            "(P10); empty after OCR-only degradation (MT-1.13-05); null "
            "for other formats."
        ),
    )
    image_base64 = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        help_text="image_base64 only: the normalized image (Section 9.5 stage 2).",
    )
    media_type = serializers.CharField(
        allow_null=True,
        help_text="image_base64 only: the normalized image's media type (always image/png).",
    )
    page_number = serializers.IntegerField(
        allow_null=True,
        help_text="Paginated responses only: this page's one-based number (Section 9.5).",
    )
    total_pages = serializers.IntegerField(
        allow_null=True,
        help_text=(
            "Paginated responses only: total pages — 1 for a single-page "
            "document (MT-1.14-03 convention)."
        ),
    )
    token_count = serializers.IntegerField(
        allow_null=True,
        help_text=(
            "Paginated responses only: this page's token estimate (as "
            "stored by WP-1.12) so an agent can budget context (9.5)."
        ),
    )


__all__ = ["AttachmentContentQuerySerializer", "AttachmentContentSerializer"]
