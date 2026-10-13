"""Submission endpoints — Section 9.2 Submission row (WP-3.2; FR-AUD-01).

One route triplet:

* ``POST /tasks/{id}/resolution`` (caller **Agent**, §12.2 "Submit
  resolution: lease owner"): validates the Section 10.5 input, then runs
  the whole submission — lock, fencing, authoritative parse, artifact
  store, scope verdict, one T7/T8/T10 dispatch — inside
  ``services.resolutions.submit_resolution``, answering 201 with the
  stored Section 7.2 row plus the post-transition task identity the
  bridge reports to the agent (Section 10.5 outcome states).
  ``Idempotency-Key`` replays a retried submission without a second
  resolution row or a second transition (NFR-12; ADR-012).
* ``GET /tasks/{id}/resolutions`` (caller **Agent / Owner**): the
  task's attempts, newest first, cursor-paginated (pagination.md) —
  the FR-AUD-01 input the auditor flow reads.
* ``GET /resolutions/{id}/patch`` (caller **Agent / Owner**): the
  stored unified patch, or the Section 9.7 "diff too large" marker for
  oversize artifacts — one response shape either way.

Plan-wide contracts reused, never re-invented: ``HasTaskProjectScope``
+ ``CanSubmitResolution``/``CanReadResolutions`` (ADR-004; §9.2/§12.2),
the canonical ``Idempotency-Key`` replay, the §9.2 error envelope with
catalog codes only, ``AgentEndpointThrottle`` on every view (FR-SEC-05 —
the shared-class pattern WP-1.8/WP-1.11 recorded for Agent/Owner rows),
and ``parse_page_size`` + composite ``(submitted_at, id)`` cursors.

Status decisions (recorded in the WP changelog): 400 malformed
input/cursor (``VALIDATION_ERROR``; unknown resolution ids ride the
core handler's recorded generic-NotFound mapping), 401
``AUTH_REQUIRED``, 403 ``ROLE_NOT_PERMITTED`` /
``AUTH_FORBIDDEN_PROJECT`` / ``LEASE_NOT_OWNED``, 404 unknown task
(``TASK_NOT_FOUND``), 409 ``LEASE_EXPIRED`` / ``TASK_STATE_CONFLICT`` /
``SCOPE_VIOLATION``, 429 ``RATE_LIMITED``, 500 ``SERVER_ERROR`` (a
storage-backend failure — no new codes, Section 20.4 item 5).
"""

from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import RequestDataTooBig
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanSubmitResolution
from apps.core.idempotency import (
    idempotency_key_of,
    lookup_replay,
    request_fingerprint,
    store_outcome,
)
from apps.core.pagination import parse_page_size
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.core.throttling import AgentEndpointThrottle

from ..permissions import CanReadResolutions, HasTaskProjectScope
from ..serializers.resolutions import (
    ResolutionListEnvelopeSerializer,
    ResolutionListQuerySerializer,
    ResolutionPatchSerializer,
    ResolutionSubmitSerializer,
    ResolutionWriteResponseSerializer,
    resolution_payload,
    task_state_payload,
)
from ..services.resolutions import (
    assert_same_project,
    decode_resolution_cursor,
    patch_payload,
    resolution_or_404,
    resolution_page,
    submit_resolution,
)
from ..services.tasks import get_task_or_404

# The canonical idempotency header on the mutating half (Section 9.2's
# "all mutating endpoints accept an idempotency key header"; headers.md
# one spelling, never an alias).
_IDEMPOTENCY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Caller-derived key making retries safe (ADR-012; NFR-12). Reusing "
        "the key with the same request replays the original outcome instead "
        "of storing a second resolution or firing a second transition."
    ),
)

_WRITE_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
    status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer,
    status.HTTP_409_CONFLICT: ErrorEnvelopeSerializer,
    status.HTTP_429_TOO_MANY_REQUESTS: ErrorEnvelopeSerializer,
}
_READ_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
    status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer,
}


def _replay_or_none(request: Request) -> Response | None:
    """A stored same-request outcome for this ``Idempotency-Key``, if any."""
    key = idempotency_key_of(request)
    if key is None:
        return None
    replay = lookup_replay(request, key, request_fingerprint(request, request.data))
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
        request_fingerprint(request, request.data),
        status=response.status_code,
        body=response.data,
    )


def _caller_project(request: Request) -> str | None:
    """The token's project scope (Section 9.3 step 1 — never a body value).

    Agent callers always carry one (WP-1.2); owner/device credentials
    are not project-bound and answer ``None`` (no scope filter).
    """
    project_id = getattr(request.auth, "project_id", None)
    return str(project_id) if project_id is not None else None


class ResolutionSubmitView(APIView):
    """``POST /tasks/{id}/resolution`` — the Submission row's write half."""

    permission_classes: list[Any] = [HasTaskProjectScope, CanSubmitResolution]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="submit_resolution",
        request=ResolutionSubmitSerializer,
        responses={
            status.HTTP_201_CREATED: ResolutionWriteResponseSerializer,
            **_WRITE_ERRORS,
        },
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Store the lease-owner agent's submission and fire exactly one "
            "Section 8.2 row (Section 9.2 Submission row; caller: Agent, "
            "lease owner — §12.2). One transaction: verify the fencing pair "
            "(`session_id` + `lease_generation`) against the locked row, "
            "parse the uploaded unified patch into the authoritative "
            "`changed_files`/`diff_summary` (bridge claims are provisional "
            "and replaced — Section 9.7), store the Task Resolution "
            "(one per attempt, Section 7.2) and its patch artifact (5 MB "
            "cap with the Section 9.7 stats-only degraded path), evaluate "
            "scope against `target_scope` through the single shared glob "
            "matcher (Section 12.3), then dispatch: out-of-scope → T8 "
            "`in_human_review` + `scope_violation`, self-flag → T8 + "
            "`self_flagged` (scope wins when both hold), clean + "
            "`audit_required` → T7 `to_be_audited`, `audit_required` false "
            "→ the T10 policy seam (fail-closed escalate; approve only via "
            "the Policy Engine — Section 8.5). `Idempotency-Key` replays a "
            "retried submission with no second row and no second "
            "transition (NFR-12). Rejections: LEASE_NOT_OWNED (403), "
            "LEASE_EXPIRED/TASK_STATE_CONFLICT/SCOPE_VIOLATION (409), "
            "TASK_NOT_FOUND (404), AUTH_FORBIDDEN_PROJECT (403)."
        ),
    )
    def post(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Store one submission; return the row + the transition outcome."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        try:
            raw_body = request.data
        except RequestDataTooBig as exc:
            # Beyond ORCHESTRATOR_REQUEST_BODY_MAX_BYTES the framework
            # refuses the body before parsing: a recorded mapping to the
            # closed catalog's VALIDATION_ERROR (400) — never a 500, and
            # never an invented 413 code (Section 20.4 item 5).
            raise ValidationError(
                "Request body exceeds ORCHESTRATOR_REQUEST_BODY_MAX_BYTES."
            ) from exc
        input_serializer = ResolutionSubmitSerializer(data=raw_body)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)

        submission = submit_resolution(
            id,
            session_id=str(validated["session_id"]),
            lease_generation=int(validated["lease_generation"]),
            git_branch=str(validated["git_branch"]),
            commit_sha=str(validated["commit_sha"]),
            execution_summary=str(validated["execution_summary"]),
            requires_human_attention=bool(validated["requires_human_attention"]),
            risk_justification=str(validated["risk_justification"]),
            patch=str(validated["patch"]),
            changed_files=validated.get("changed_files"),
            diff_summary=validated.get("diff_summary"),
            caller_project_id=_caller_project(request),
        )
        response = Response(
            ResolutionWriteResponseSerializer(
                {
                    "resolution": resolution_payload(submission.resolution),
                    "task": task_state_payload(submission.task),
                    "trigger": submission.trigger,
                    "scope_violations": submission.verdict.as_list(),
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )
        _store_outcome(request, response)
        return response


class ResolutionListView(APIView):
    """``GET /tasks/{id}/resolutions`` — one task's submission attempts."""

    permission_classes: list[Any] = [HasTaskProjectScope, CanReadResolutions]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="list_resolutions",
        responses={
            status.HTTP_200_OK: ResolutionListEnvelopeSerializer,
            **_READ_ERRORS,
        },
        parameters=[ResolutionListQuerySerializer],
        description=(
            "One task's resolutions, newest first (Section 9.2 Submission "
            "row; caller: Agent / Owner — the FR-AUD-01 input the auditor "
            "flow reads). Cursor pagination per pagination.md: `page_size` "
            "(default 25, maximum 100), the opaque `cursor` from the "
            "previous page's `next_cursor`, stable (submitted_at, id) "
            "ordering so inserts during paging never shift or duplicate "
            "rows. Empty tasks return an empty page. Cross-project agent "
            "tokens answer AUTH_FORBIDDEN_PROJECT (403); unknown tasks "
            "TASK_NOT_FOUND (404)."
        ),
    )
    def get(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Page one task's submission history, newest first."""
        task = get_task_or_404(id)

        query = ResolutionListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], query.validated_data)

        cursor = decode_resolution_cursor(validated.get("cursor") or None)
        page_size = parse_page_size(validated.get("page_size"))
        rows, next_cursor = resolution_page(task, cursor=cursor, page_size=page_size)
        return Response(
            ResolutionListEnvelopeSerializer(
                {
                    "results": [resolution_payload(row) for row in rows],
                    "next_cursor": next_cursor,
                }
            ).data
        )


class ResolutionPatchView(APIView):
    """``GET /resolutions/{id}/patch`` — serve the artifact or the marker."""

    permission_classes: list[Any] = [CanReadResolutions]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="get_resolution_patch",
        responses={
            status.HTTP_200_OK: ResolutionPatchSerializer,
            **_READ_ERRORS,
        },
        description=(
            "The stored unified patch for one resolution (Section 9.2 "
            "Submission row; caller: Agent / Owner). One response shape "
            "covers both Section 9.7 paths: patches up to the 5 MB "
            "inclusive cap serve their body (`diff_too_large` false), "
            "oversize patches serve the stats-and-file-list-only marker "
            '(`diff_too_large` true, `marker` = "diff too large") — a '
            "degraded path, never an error. sha256/size_bytes are the "
            "server-computed values from Section 7.2. The route embeds no "
            "PID, so the addressed project is checked against the token "
            "after role admission (ADR-004 zero-bleed): a foreign-project "
            "agent answers AUTH_FORBIDDEN_PROJECT (403); unknown "
            "resolution ids answer VALIDATION_ERROR (400) via the "
            "documented generic-NotFound mapping (no new codes)."
        ),
    )
    def get(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Serve one resolution's patch body, or the oversize marker."""
        resolution = resolution_or_404(id)
        assert_same_project(resolution, _caller_project(request))
        return Response(ResolutionPatchSerializer(patch_payload(resolution)).data)
