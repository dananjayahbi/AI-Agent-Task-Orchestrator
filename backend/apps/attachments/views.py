"""Attachment endpoints — Section 9.2 Attachments row (MT-1.11-03/04/05).

Routes (all under ``/api/v1`` via the root include; no trailing slashes):

* ``POST /tasks/{id}/attachments`` — multipart upload, caller **Owner**
  only (Section 9.2: agents read, never upload — MT-1.11-03). Validates
  through the MT-1.11-02 stage, stores via MT-1.11-01, creates the
  record with status ``uploaded`` (FR-ATT-07), honors the canonical
  ``Idempotency-Key`` replay (Section 9.2), and answers with the
  descriptor. De-duplicated hits answer **200** with the existing
  descriptor instead of 201 (one record, one object — Section 19
  acceptance; recorded response-shape choice).
* ``GET /tasks/{id}/attachments`` — cursor-paginated descriptor
  listing, caller Owner or the project's agent token (the Section 9.2
  read cell; WP-2.x activates the bridge's reader).
* ``GET /attachments/{id}`` — one descriptor, same access rules.
* ``DELETE /attachments/{id}`` — caller **Owner** only; refused with
  409 ``TASK_STATE_CONFLICT`` on completed/archived tasks (Section
  16.3's retention rule — MT-1.11-05); otherwise soft-deletes.

Status decisions (recorded in the WP changelog): 400 ``VALIDATION_ERROR``
(malformed input/cursor/unknown attachment — the catalog has no
attachment code, so the generic NotFound maps there like projects),
401 ``AUTH_REQUIRED``, 403 ``ROLE_NOT_PERMITTED`` /
``AUTH_FORBIDDEN_PROJECT``, 404 ``TASK_NOT_FOUND``, 409
``TASK_STATE_CONFLICT``, 415 ``ATTACHMENT_UNSUPPORTED_FORMAT``, 429
``RATE_LIMITED`` (agent-token reads ride the agent budget — the same
recorded choice WP-1.8 made for the shared checkpoints route; owner
sessions are unaffected in practice because FR-SEC-05 scopes budgets to
agent/device tokens, but the class is wired for the agent-read cell).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsOwnerSession
from apps.core.idempotency import (
    idempotency_key_of,
    lookup_replay,
    request_fingerprint,
    store_outcome,
)
from apps.core.pagination import parse_page_size
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.core.throttling import AgentEndpointThrottle
from apps.tasks.permissions import HasTaskProjectScope
from apps.tasks.services.tasks import get_task_or_404

from .listing import attachment_page, decode_attachment_cursor
from .models import TaskAttachment
from .permissions import CanReadAttachments, HasAttachmentProjectScope
from .retention import delete_attachment
from .serializers import (
    AttachmentDeleteSerializer,
    AttachmentListEnvelopeSerializer,
    AttachmentListQuerySerializer,
    AttachmentSerializer,
    attachment_descriptor,
)
from .services import create_attachment

# The canonical idempotency header on the mutating halves (Section 9.2:
# "All mutating endpoints accept an idempotency key header"; headers.md
# one spelling, never an alias).
_IDEMPOTENCY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Caller-derived key making retries safe (ADR-012; NFR-12). Reusing "
        "the key with the same upload replays the original response instead "
        "of storing a second copy; reusing it with a different upload is an "
        "open point (headers.md) and executes normally."
    ),
)

_ERRORS_4X5 = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
}
_TASK_ERRORS = {**_ERRORS_4X5, status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer}
_UPLOAD_ERRORS = {
    **_TASK_ERRORS,
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: ErrorEnvelopeSerializer,
    status.HTTP_429_TOO_MANY_REQUESTS: ErrorEnvelopeSerializer,
}
_DELETE_ERRORS = {
    **_ERRORS_4X5,
    status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer,
    status.HTTP_409_CONFLICT: ErrorEnvelopeSerializer,
}


def _multipart_fingerprint_body(request: Request) -> dict[str, Any]:
    """The stable fingerprint material for one multipart request.

    The fingerprint hashes the multipart body's textual fields plus the
    file's own (name, size) pair — files stream, so the full content is
    not hashed here; the de-duplication stage catches same-bytes repeats
    even when the fingerprint differs (the layered design: idempotency
    for retries, content addressing for equality). ``request.data`` is
    narrowed to a mapping (a list body carries no parts to hash).
    """
    data: Any = request.data
    fields = (
        {name: value for name, value in data.items() if name != "file" and isinstance(value, str)}
        if isinstance(data, Mapping)
        else {}
    )
    file = data.get("file") if isinstance(data, Mapping) else None
    return {
        "fields": fields,
        "file": {
            "name": getattr(file, "name", None),
            "size": getattr(file, "size", None),
        },
    }


def _replay_or_none(request: Request) -> Response | None:
    """A stored same-request outcome for this ``Idempotency-Key``, if any."""
    key = idempotency_key_of(request)
    if key is None:
        return None
    replay = lookup_replay(
        request, key, request_fingerprint(request, _multipart_fingerprint_body(request))
    )
    if replay is None:
        return None
    return Response(replay["body"], status=replay["status"])


def _store_outcome(request: Request, response: Response) -> None:
    """Record a successful outcome under this key (2xx only)."""
    key = idempotency_key_of(request)
    if key is None:
        return
    store_outcome(
        request,
        key,
        request_fingerprint(request, _multipart_fingerprint_body(request)),
        status=response.status_code,
        body=response.data,
    )


def _uploaded_by(request: Request) -> str | None:
    """Actor reference for Section 7.2's ``uploaded_by`` (user id, or None)."""
    user = getattr(request, "user", None)
    user_id = getattr(user, "pk", None)
    return str(user_id) if user_id is not None else None


class AttachmentListCreateView(APIView):
    """``POST`` (multipart upload — MT-1.11-03) + ``GET`` (listing — MT-1.11-04)."""

    # Scope first (ADR-004 zero-bleed outranks role errors), then the
    # Section 9.2 caller cells per method: POST Owner-only, GET Owner or
    # the project's agent token. The shared view carries the agent-read
    # budget class (WP-1.8's recorded pattern for shared routes).
    permission_classes: list[Any] = [HasTaskProjectScope, IsOwnerSession]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [AgentEndpointThrottle]

    def get_permissions(self) -> list[Any]:
        """POST answers the Owner cell; GET the Owner/Agent read cell."""
        if self.request is not None and self.request.method == "GET":
            return [HasTaskProjectScope(), CanReadAttachments()]
        return [HasTaskProjectScope(), IsOwnerSession()]

    @extend_schema(
        operation_id="upload_attachment",
        request={"multipart/form-data": AttachmentSerializer},
        responses={status.HTTP_201_CREATED: AttachmentSerializer, **_UPLOAD_ERRORS},
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Upload one attachment (Section 9.2; caller: Owner only — agents "
            "read, never upload). The multipart body carries the file part "
            "`file`; limits and the allowlist are Section 9.5's (25 MB per "
            "file, 10 per task, 100 MB total — configurable defaults), the "
            "MIME type is **sniffed from the content**, never taken from the "
            "extension or the declared type, and a mismatch is rejected "
            "(415 ATTACHMENT_UNSUPPORTED_FORMAT; oversize/over-count/over-"
            "total answer 400 VALIDATION_ERROR). Identical bytes already "
            "attached to the task de-duplicate onto the existing record (200 "
            "instead of 201 — one record, one stored object). The response "
            "is the FR-ATT-03 descriptor with processing_status `uploaded` "
            "(FR-ATT-07); `token_count` and `short_description` are null "
            "until the WP-1.12 pipeline fills them. `Idempotency-Key` "
            "replays a retried upload without duplicating (ADR-012). The "
            "pipeline enqueue hook hands the job to the Celery worker "
            'after commit (Section 9.9 "on upload"; MT-1.12-01 — the '
            "unit layer keeps a documented no-op seam)."
        ),
    )
    def post(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Accept one multipart upload; answer with its descriptor."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        task = get_task_or_404(id)
        data: Any = request.data
        upload = data.get("file") if isinstance(data, Mapping) else None
        if upload is None or not hasattr(upload, "read"):
            raise ValidationError({"file": "The multipart body must carry a `file` part."})

        outcome = create_attachment(
            task_id=task.pk,
            filename=str(getattr(upload, "name", "")),
            declared_mime=getattr(upload, "content_type", None),
            data=cast(Any, upload).read(),
            uploaded_by=_uploaded_by(request),
        )
        response = Response(
            attachment_descriptor(outcome.attachment),
            status=(status.HTTP_200_OK if outcome.deduplicated else status.HTTP_201_CREATED),
        )
        _store_outcome(request, response)
        return response

    @extend_schema(
        operation_id="list_task_attachments",
        responses={status.HTTP_200_OK: AttachmentListEnvelopeSerializer, **_TASK_ERRORS},
        parameters=[AttachmentListQuerySerializer],
        description=(
            "List one task's attachment descriptors (Section 9.2; caller: "
            "Owner or the project's agent token). Newest first "
            "(`created_at`, then id — stable, deterministic, pagination.md "
            "rule 2). Descriptors carry `id`, `filename`, `size`, "
            "`processing_status` plus FR-ATT-03's `token_count` and "
            "`short_description`, which are null until the WP-1.12 pipeline "
            "produces them. Pagination is cursor-based: pass `cursor` from "
            "the previous `next_cursor` *for this task only* (rule 1); "
            "`page_size` defaults to 25, clamped to 100. Soft-deleted "
            "attachments are excluded. Cross-project agent tokens answer "
            "AUTH_FORBIDDEN_PROJECT (403)."
        ),
    )
    def get(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """One cursor page of the task's attachment descriptors."""
        task = get_task_or_404(id)
        query = AttachmentListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], query.validated_data)

        cursor = decode_attachment_cursor(validated.get("cursor"))
        page_size = parse_page_size(validated.get("page_size"))
        rows, next_cursor = attachment_page(task, cursor=cursor, page_size=page_size)
        return Response(
            {
                "results": [attachment_descriptor(row) for row in rows],
                "next_cursor": next_cursor,
            }
        )


class AttachmentDetailView(APIView):
    """``GET`` (one descriptor — MT-1.11-04) + ``DELETE`` (MT-1.11-05)."""

    # The PID does not ride inside the UUID — the scope guard resolves
    # the row's task's project (ADR-004; never from the body — G-07).
    permission_classes: list[Any] = [HasAttachmentProjectScope, IsOwnerSession]
    throttle_classes = [AgentEndpointThrottle]

    def get_permissions(self) -> list[Any]:
        """GET answers the Owner/Agent read cell; DELETE stays Owner-only."""
        if self.request is not None and self.request.method == "GET":
            return [HasAttachmentProjectScope(), CanReadAttachments()]
        return [HasAttachmentProjectScope(), IsOwnerSession()]

    def _resolve(self, request: Request) -> TaskAttachment:
        """The addressed attachment, boundary-validated; unknown → 400.

        The closed catalog has no attachment-specific not-found code
        (Section 20.4 item 5), so a malformed or unknown id follows the
        recorded generic mapping: DRF ``ValidationError``/``NotFound`` →
        ``VALIDATION_ERROR`` (400) — the same asymmetry the projects app
        carries (MT-1.3-03).
        """
        from uuid import UUID

        raw = str(self.kwargs["id"])
        try:
            UUID(raw)
        except ValueError as exc:
            raise ValidationError({"id": "Not a valid attachment id."}) from exc
        # Live rows only: a soft-deleted record is unknown to the API
        # (MT-1.11-05 idempotency reading — no second storage decision).
        # DRF's NotFound (not Django's Http404) so the envelope handler
        # applies the recorded 400/VALIDATION_ERROR generic mapping.
        attachment = TaskAttachment.objects.filter(deleted_at__isnull=True, pk=raw).first()
        if attachment is None:
            raise NotFound("Attachment does not exist.")
        return attachment

    @extend_schema(
        operation_id="retrieve_attachment",
        responses={status.HTTP_200_OK: AttachmentSerializer, **_TASK_ERRORS},
        description=(
            "Read one attachment descriptor by id (Section 9.2; caller: "
            "Owner or an agent token scoped to the attachment's project). "
            "`token_count` and `short_description` are null until the "
            "WP-1.12 pipeline fills them (FR-ATT-03/07). Foreign agent "
            "tokens answer AUTH_FORBIDDEN_PROJECT (403); unknown or "
            "malformed ids answer VALIDATION_ERROR (400 — the catalog has "
            "no attachment not-found code; recorded mapping)."
        ),
    )
    def get(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Fetch one attachment descriptor by UUID."""
        return Response(attachment_descriptor(self._resolve(request)))

    @extend_schema(
        operation_id="delete_attachment",
        responses={status.HTTP_200_OK: AttachmentDeleteSerializer, **_DELETE_ERRORS},
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Delete one attachment (Section 9.2; caller: Owner only). "
            "Resolved conservatively against Section 16.3: on a completed "
            "or archived task the call answers 409 TASK_STATE_CONFLICT — "
            "the retention job owns those bytes (archive plus the "
            "configurable grace period, Section 12.4; OQ-10 default 30 "
            "days). On any earlier state the record is soft-deleted "
            "(`deleted_at` stamped) and the stored object is removed only "
            "when no other de-duplicated record shares its content key. "
            "`Idempotency-Key` replays a retried DELETE's response "
            "(ADR-012)."
        ),
    )
    def delete(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Soft-delete one attachment; remove unreferenced bytes."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        attachment = self._resolve(request)
        outcome = delete_attachment(attachment)
        response = Response(
            {
                "id": outcome.attachment.pk,
                "task_id": outcome.attachment.task_id,
                "deleted_at": outcome.attachment.deleted_at,
            }
        )
        _store_outcome(request, response)
        return response


__all__ = ["AttachmentDetailView", "AttachmentListCreateView"]
