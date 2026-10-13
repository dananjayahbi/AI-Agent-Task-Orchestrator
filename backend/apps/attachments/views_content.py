"""``GET /attachments/{id}/content`` — the Section 9.5 retrieval endpoint
(FR-ATT-04; MT-1.14-02/03/04/05).

Caller cell is the Attachments read cell (Section 9.2: Owner / Agent
read): :class:`~apps.attachments.permissions.HasAttachmentProjectScope`
resolves the UUID to its project (ADR-004 zero-bleed — cross-project
agent tokens answer ``AUTH_FORBIDDEN_PROJECT``) and
:class:`~apps.attachments.permissions.CanReadAttachments` admits owner
sessions and agent tokens, devices and anonymous denied. Malformed or
unknown ids follow the recorded generic mapping (400
``VALIDATION_ERROR`` — the catalog has no attachment not-found code),
mirroring :class:`apps.attachments.views.AttachmentDetailView`.

Behavior, each owned by a micro-task:

* **Format resolution** (MT-1.14-02) — the Section 9.5 table via
  :mod:`apps.attachments.retrieval`; the text-safe ``auto`` default of
  Section 10.4 step 4; unsupported combinations answer the catalog
  ``ATTACHMENT_UNSUPPORTED_FORMAT`` (415).
* **Pagination** (MT-1.14-03) — the ``page`` parameter, one-based, the
  Section 9.5 ``page_number``/``total_pages``/token-count metadata;
  out-of-range and invalid values answer ``VALIDATION_ERROR``; unknown
  query parameters are rejected (the strict query serializer).
* **Untrusted banner** (MT-1.14-04) — every delivered text value is
  passed through :func:`apps.attachments.banner.mark_untrusted` at this
  boundary, once; the binary image payload is never prefixed.
* **Errors** (MT-1.14-05) — non-``ready`` attachments answer 409
  ``ATTACHMENT_NOT_READY`` for *every* format (``failed`` carries the
  stored human-readable reason); error envelopes are never
  banner-prefixed (the banner applies to text payloads only).
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from apps.core.serializers import ErrorEnvelopeSerializer
from apps.core.throttling import AgentEndpointThrottle

from .banner import mark_untrusted
from .exceptions import AttachmentNotReady, AttachmentUnsupportedFormat
from .models import ProcessingStatus, TaskAttachment
from .permissions import CanReadAttachments, HasAttachmentProjectScope
from .retrieval import (
    FORMAT_AUTO,
    FORMAT_IMAGE_BASE64,
    FORMAT_TEXT_OCR,
    UnsupportedFormatCombination,
    content_page,
    resolve_format,
)
from .serializers_content import (
    AttachmentContentQuerySerializer,
    AttachmentContentSerializer,
)

# Declared error responses (the OpenAPI contract): the recorded generic
# mapping (400), the authz pair (401/403), the not-while-processing 409
# (Section 9.5) and the unsupported-format 415 (Section 9.5 table).
_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
    status.HTTP_409_CONFLICT: ErrorEnvelopeSerializer,
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: ErrorEnvelopeSerializer,
}


def _resolve_live_attachment(raw: str) -> TaskAttachment:
    """The addressed live attachment; malformed/unknown → 400 (recorded).

    Mirrors ``AttachmentDetailView._resolve`` (same UUID boundary, same
    soft-delete blindness — a deleted record is unknown to the API).
    """
    from uuid import UUID

    try:
        UUID(raw)
    except ValueError as exc:
        raise ValidationError({"id": "Not a valid attachment id."}) from exc
    attachment = TaskAttachment.objects.filter(deleted_at__isnull=True, pk=raw).first()
    if attachment is None:
        raise NotFound("Attachment does not exist.")
    return attachment


class AttachmentContentView(APIView):
    """The Section 9.2 content retrieval route (MT-1.14-02)."""

    permission_classes: list[Any] = [HasAttachmentProjectScope, CanReadAttachments]
    throttle_classes = [AgentEndpointThrottle]

    def perform_content_negotiation(self, request: Request, force: bool = False) -> Any:
        """Section 9.5 owns ``format`` **on this route** — Accept only here.

        DRF reserves the query parameter named by its global
        ``URL_FORMAT_OVERRIDE`` (``format``) for *renderer* selection and
        answers an unknown value with an internal Http404 — which would
        404 every retrieval preference (``auto``/``image_base64``/
        ``text_ocr``/``markdown`` are not renderer names). Section 9.2
        fixes the parameter's spelling for this endpoint
        (``content?format=&page=``), so the plan's name wins: this view
        negotiates on the Accept header alone (the JSON default).
        Recorded per-view opt-out (WP-1.14 changelog) — deliberately not
        a global rename, which would break the schema route's documented
        ``?format=json``; the view still reads the real query params.
        """
        renderers = self.get_renderers()
        conneg = self.get_content_negotiator()
        override = api_settings.URL_FORMAT_OVERRIDE
        django_request = request._request
        original_get = django_request.GET
        if override in original_get:
            filtered = original_get.copy()
            filtered.pop(override)
            # cached_property: instance-dict override; the cast sidesteps the
            # read-only QueryDict annotation (the object itself is not frozen).
            django_request.GET = cast(Any, filtered)
        try:
            return conneg.select_renderer(request, renderers, self.format_kwarg)
        except Exception:
            if force:
                return (renderers[0], renderers[0].media_type)
            raise
        finally:
            django_request.GET = original_get

    @extend_schema(
        operation_id="retrieve_attachment_content",
        responses={status.HTTP_200_OK: AttachmentContentSerializer, **_ERRORS},
        parameters=[AttachmentContentQuerySerializer],
        description=(
            "Retrieve one attachment's content (Section 9.2; caller: Owner "
            "or an agent token scoped to the attachment's project). The "
            "`format` parameter follows the Section 9.5 retrieval table: "
            "`auto` (default) is text-safe — documents resolve to paginated "
            "`markdown`, images to `text_ocr` (OCR transcript plus layout "
            "description); `image_base64` serves the normalized image and "
            "answers ATTACHMENT_UNSUPPORTED_FORMAT (415) for non-images; "
            "`markdown` and `text_ocr` answer 415 where the attachment has "
            "no such representation. `page` is one-based (the "
            "pagination.md content exception): paginated responses carry "
            "`page_number`, `total_pages` and the page's token count so an "
            "agent can budget context; non-paginated responses omit them. "
            "Every delivered text value is prefixed with the "
            "untrusted-content banner (P10). Attachments not `ready` answer "
            "409 ATTACHMENT_NOT_READY (`failed` includes the stored reason). "
            "Unknown `format`/`page` values and unknown query parameters "
            "answer VALIDATION_ERROR (400)."
        ),
    )
    def get(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """One content unit for the addressed attachment."""
        attachment = _resolve_live_attachment(str(id))

        query = AttachmentContentQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], query.validated_data)
        requested = str(validated.get("format", FORMAT_AUTO))
        page = int(validated.get("page", 1))

        # MT-1.14-05: every non-ready status answers the catalog 409 —
        # `failed` adds the stored human-readable reason (FR-ATT-07
        # visibility on the read path; the reason is ours, Section 12.4).
        if attachment.processing_status != ProcessingStatus.READY:
            detail = f"The attachment is {attachment.processing_status}, not ready."
            if (
                attachment.processing_status == ProcessingStatus.FAILED
                and attachment.failure_detail
            ):
                detail = f"{detail} Failure reason: {attachment.failure_detail}"
            raise AttachmentNotReady(detail)

        try:
            resolved = resolve_format(attachment, requested)
        except UnsupportedFormatCombination as exc:
            raise AttachmentUnsupportedFormat(str(exc)) from exc

        try:
            page_data = content_page(attachment, resolved=resolved, page=page)
        except IndexError as exc:
            raise ValidationError({"page": str(exc)}) from exc

        payload: dict[str, Any] = {
            "attachment_id": attachment.pk,
            "format": page_data.format,
            "content": None,
            "description": None,
            "image_base64": None,
            "media_type": None,
            "page_number": page_data.page_number,
            "total_pages": page_data.total_pages,
            "token_count": page_data.token_count,
        }
        if page_data.format == FORMAT_IMAGE_BASE64:
            payload["image_base64"] = page_data.image_base64
            payload["media_type"] = page_data.media_type
        else:
            # The delivery boundary is the one banner layer (MT-1.14-04):
            # every text field exactly once; stored text stays un-decorated.
            payload["content"] = mark_untrusted(page_data.content or "")
            if page_data.format == FORMAT_TEXT_OCR:
                payload["description"] = mark_untrusted(page_data.description or "")
        return Response(AttachmentContentSerializer(payload).data)


__all__ = ["AttachmentContentView"]
