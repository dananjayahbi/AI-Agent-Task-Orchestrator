"""The submission write path — Sections 7.2/9.2/9.7/12.3 (WP-3.2).

Layers, one module (mirroring ``services.checkpoints``'s structure):

* :func:`store_patch_artifact` (MT-3.2-02) — content-derived key, the
  Section 9.7 5 MB cap with the degraded *stats-and-file-list-only*
  path for oversize patches, server-computed ``sha256``/``size_bytes``.
* :func:`submit_resolution` (MT-3.2-01 + 03 + 04 + 05) — the whole
  submission in **one transaction**: lock the task, scope check, run the
  shared fencing gate, parse the patch (authoritative stats/files),
  store the resolution + artifact, evaluate scope with the single
  matcher, then dispatch exactly one of T7/T8/T10 through the state
  machine (Section 9.1: ``tasks`` owns all state changes).
* the listing query + cursor helpers (MT-3.2-01) — reverse-chronological
  per-task paging per docs/plan/conventions/pagination.md.

Recorded readings (Section 20.1 item 5 — no hidden decisions):

* **Patch rides the submission body.** Section 9.2 exposes no separate
  patch-upload route (``GET /resolutions/{id}/patch`` only *serves*),
  so the bridge's captured unified diff travels on
  ``POST /tasks/{id}/resolution`` as a JSON string — Section 10.5's
  "captures patch and file list, uploads" in one call. ``sha256`` is
  computed over the UTF-8 encoding of that text (server-side, never
  trusted from the client).
* **Provisional claims are accepted and ignored.** The bridge sends its
  locally captured ``changed_files``/``diff_summary`` (MT-2.6-04); the
  server stores *its own* parse (Section 9.7 — claims never override,
  and the two are never merged).
* **The 5 MB cap is inclusive** (MT-3.2-02 risk note): a patch of
  exactly 5 * 1024 * 1024 bytes stores fully; one byte more takes the
  degraded path — stats and file list are still parsed and stored, the
  body is dropped, and ``GET .../patch`` answers with the Section 9.7
  marker. The cap is a module constant, not a setting: Section 9.7
  fixes the default and making it configurable is explicitly out of
  scope for this WP.
* **Trigger precedence** (MT-3.2-05): scope violation beats
  ``self_flagged`` when both hold (the MT risk note's recorded choice —
  "prefer ``self_flagged`` only when scope is clean"); either beats
  ``audit_required`` (T8 first); ``audit_required`` false reaches the
  T10 seam last.
* **Storage failures** surface as the catalog ``SERVER_ERROR`` through
  the standard envelope handler (no new codes; Section 20.4 item 5) —
  the degraded oversize path is *not* a failure (Section 9.7).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, NamedTuple, cast
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.exceptions import AuthForbiddenProject
from apps.attachments.storage import content_key, get_storage, hash_bytes
from apps.core.pagination import decode_str_cursor, encode_cursor
from apps.leases.fencing import require_current_lease

from ..exceptions import TaskNotFound, TaskStateConflict
from ..models import ReviewReason, Task, TaskArtifact, TaskResolution, TaskState
from ..state_machine.dispatcher import dispatch_transition
from ..state_machine.transitions_submission import (
    ensure_submission_wired,
    resolve_policy_decision,
)
from .ids import ensure_valid_task_id
from .patch_parse import parse_unified_diff
from .scope import ScopeVerdict, evaluate_scope

# Section 9.7: "Size cap (default 5 MB)" — inclusive, and deliberately a
# constant: MT-3.2-02 puts configurability beyond the default out of
# scope (the documented default is never re-decided here).
PATCH_MAX_BYTES: int = 5 * 1024 * 1024

# The Section 9.7 "diff too large" marker the viewers render (§13.2's
# "diff too large" fallback) — the literal string served in place of the
# oversize body, recorded here so producers and viewers agree.
DIFF_TOO_LARGE_MARKER: str = "diff too large"


def patch_storage_key(sha256_hex: str) -> str:
    """Content-derived key for a stored patch body (MT-3.2-02; §9.10).

    The shared ``objects/`` content namespace the storage Protocol
    sanctions for patch artifacts ("attachments now, patch artifacts in
    M3"): identical bytes dedupe to one object across stores. Recorded
    risk (WP changelog): an object shared with an attachment whose
    retention later deletes it would take the patch body with it —
    Section 9.9's retention job owns that ref-count question (flagged
    as an OQ for WP-6.x, not papered over here).
    """
    return content_key(sha256_hex)


@dataclass(frozen=True)
class ResolutionSubmission:
    """One accepted submission's outcome (the endpoint's response source)."""

    resolution: TaskResolution
    artifact: TaskArtifact
    verdict: ScopeVerdict
    task: Task  # the post-transition row the dispatcher returned
    trigger: str  # which Section 8.2 row fired ("submit", ...)


def store_patch_artifact(resolution: TaskResolution, patch: str) -> TaskArtifact:
    """MT-3.2-02: hash, cap, and (when within it) store the patch body.

    Degraded path (Section 9.7): oversize patches are **not** rejected —
    the artifact row still records the server-computed ``sha256`` and
    ``size_bytes`` (and the resolution already carries the parsed stats
    and file list); only the body is skipped, which is exactly what the
    patch GET keys its marker on.
    """
    data = patch.encode("utf-8")
    digest = hash_bytes(data)
    oversize = len(data) > PATCH_MAX_BYTES
    key = "" if oversize else patch_storage_key(digest)
    if not oversize:
        get_storage().put(key, data)  # failures → SERVER_ERROR envelope
    return TaskArtifact.objects.create(
        resolution=resolution,
        kind="patch",
        storage_key=key,
        size_bytes=len(data),
        sha256=digest,
    )


def submit_resolution(
    task_id: str,
    *,
    session_id: str,
    lease_generation: int,
    git_branch: str,
    commit_sha: str,
    execution_summary: str,
    requires_human_attention: bool = False,
    risk_justification: str = "",
    patch: str = "",
    changed_files: list[str] | None = None,
    diff_summary: dict[str, Any] | None = None,
    caller_project_id: str | None = None,
) -> ResolutionSubmission:
    """Store the submission and fire exactly one Section 8.2 row.

    ``changed_files``/``diff_summary`` are accepted (Section 10.5's
    bridge-captured claims) and **ignored**: the stored patch's parse
    wins outright (Section 9.7). Everything — lock, fencing, parse,
    store, scope verdict, dispatch — commits or rolls back together
    (Section 8.2 rule 2), so a refused transition never leaves a
    resolution row behind.
    """
    ensure_valid_task_id(task_id)
    ensure_submission_wired()  # lazy WP-1.6-style wiring (its docstring)

    with transaction.atomic():
        task = Task.objects.select_for_update().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(f"Task {task_id} does not exist.")
        if caller_project_id is not None and task.project_id != caller_project_id:
            raise AuthForbiddenProject(
                f"Token is scoped to {caller_project_id!r}, not {task.project_id!r}."
            )
        if task.state != TaskState.IN_PROGRESS:
            # Cheap early refusal: only an in_progress task is open to a
            # submission (the dispatcher would answer the same 409 — this
            # keeps the rejection before any parse work).
            raise TaskStateConflict(
                task.pk,
                reason=f"is {task.state}, not in_progress (no submission accepted)",
            )
        # MT-3.2-01: the shared gate under the row lock (no second
        # implementation — LEASE_EXPIRED 409 / LEASE_NOT_OWNED 403).
        require_current_lease(task, session_id=session_id, lease_generation=lease_generation)

        attempt = task.attempt_number
        if TaskResolution.objects.filter(task=task, attempt_number=attempt).exists():
            # Section 7.2's cardinality, answered with the catalog code
            # instead of leaking an IntegrityError (a replay with the
            # same Idempotency-Key never reaches here — the view's
            # replay cache answers first).
            raise TaskStateConflict(
                task.pk,
                reason=f"already has a resolution for attempt {attempt}",
            )

        # MT-3.2-03: the authoritative parse — provisional claims die here.
        parsed = parse_unified_diff(patch)
        resolution = TaskResolution.objects.create(
            task=task,
            attempt_number=attempt,
            branch_name=git_branch,
            commit_sha=commit_sha,
            execution_summary=execution_summary,
            diff_summary=parsed.as_diff_summary(),
            changed_files=list(parsed.changed_files),
            requires_human_attention=bool(requires_human_attention),
            risk_justification=risk_justification,
            submitted_by_session=session_id,
        )
        artifact = store_patch_artifact(resolution, patch)

        # MT-3.2-04: one verdict from the shared matcher, read by the T8
        # guard below (and recomputable by rule R2 from resolution's
        # changed_files through the same function).
        verdict = evaluate_scope(list(task.target_scope or []), parsed.changed_files)

        # MT-3.2-05 ordering: scope first (scope beats self-flag), then
        # the flag, then audit_required, then the T10 engine seam.
        reason: str | None
        if not verdict.ok:
            trigger = "submit_flagged"
            reason = ReviewReason.SCOPE_VIOLATION
        elif resolution.requires_human_attention:
            trigger = "submit_flagged"
            reason = ReviewReason.SELF_FLAGGED
        elif not task.audit_required:
            decision = resolve_policy_decision(task, resolution, verdict)
            if decision.approve:
                trigger = "submit_policy_approved"
                reason = None  # the row's own default catalog code
            else:
                trigger = "submit_unreviewed"
                reason = decision.reason
        else:
            trigger = "submit"
            reason = None

        note = "" if verdict.ok else f"out of scope: {', '.join(verdict.violations)}"
        updated = dispatch_transition(
            task_id=task.pk,
            trigger=trigger,
            actor_type="agent",
            actor_ref=session_id,
            reason_code=reason,
            note=note,
            extra={
                "session_id": session_id,
                "lease_generation": lease_generation,
                "resolution": resolution,
                "scope_verdict": verdict,
                # T8's side effect reads the strict pair back out of the
                # context (validated there against T8_REVIEW_REASONS);
                # None on the T7/T10 rows, which never consult it.
                "review_reason": reason,
            },
        )
        return ResolutionSubmission(
            resolution=resolution,
            artifact=artifact,
            verdict=verdict,
            task=updated,
            trigger=trigger,
        )


# --- serving the stored patch (Section 9.2 GET /resolutions/{id}/patch) ------


def resolution_or_404(resolution_id: UUID | str) -> TaskResolution:
    """One resolution by id — unknown ids answer the documented mapping.

    The catalog has no resolution-scoped not-found code (Section 9.2),
    so the generic DRF ``NotFound`` flows through the envelope handler's
    recorded mapping to ``VALIDATION_ERROR`` (400) — see
    ``apps.core.exceptions``' docstring; no code is invented here.
    """
    try:
        return cast(TaskResolution, TaskResolution.objects.get(pk=resolution_id))
    except (TaskResolution.DoesNotExist, ValueError, DjangoValidationError):
        raise NotFound("Resolution does not exist.") from None


def patch_payload(resolution: TaskResolution) -> dict[str, Any]:
    """The patch GET body: stored patch, or the Section 9.7 marker.

    Exactly one shape (one OpenAPI schema): ``diff_too_large`` flips
    when the artifact exceeds the cap, ``patch`` carries the body or
    ``None``, and ``marker`` spells the literal the viewers render.
    A resolution without a patch artifact is a server-side gap and
    answers the catalog ``SERVER_ERROR`` (existing code — no new one).
    """
    artifact = resolution.artifacts.filter(kind="patch").first()
    if artifact is None:  # pragma: no cover - every submit stores one
        raise NotFound("Resolution does not exist.")
    base: dict[str, Any] = {
        "resolution_id": str(resolution.pk),
        "kind": artifact.kind,
        "sha256": artifact.sha256,
        "size_bytes": artifact.size_bytes,
    }
    if artifact.size_bytes > PATCH_MAX_BYTES:
        return {
            **base,
            "diff_too_large": True,
            "patch": None,
            "marker": DIFF_TOO_LARGE_MARKER,
        }
    body = get_storage().get(artifact.storage_key)  # failures → SERVER_ERROR
    return {
        **base,
        "diff_too_large": False,
        "patch": body.decode("utf-8", errors="replace"),
        "marker": None,
    }


def assert_same_project(resolution: TaskResolution, caller_project_id: str | None) -> None:
    """ADR-004 zero-bleed for the resolution-addressed route.

    ``/resolutions/{id}`` embeds no PID (the id is a UUID), so the
    scope guard the task-addressed routes get from the URL has to run
    here against the owning task's project — agent tokens for any other
    project answer ``AUTH_FORBIDDEN_PROJECT`` before role logic.
    """
    task = resolution.task
    if caller_project_id is not None and task.project_id != caller_project_id:
        raise AuthForbiddenProject(
            f"Token is scoped to {caller_project_id!r}, not {task.project_id!r}."
        )


# --- listing (MT-3.2-01; WP-0.5-04 cursor conventions) -----------------------


class ResolutionCursorKey(NamedTuple):
    """The composite sort key a listing cursor resumes from (opaque outside)."""

    submitted_at: datetime
    resolution_id: UUID


def resolution_list_queryset(task: Task) -> QuerySet[TaskResolution]:
    """One task's resolutions, newest first (the auditor's FR-AUD-01 view).

    Ordering is ``(-submitted_at, -id)``: the server timestamp leads,
    the UUID primary key breaks ties deterministically (pagination.md
    rule 2); the ``resolution_task_time`` index serves the scan.
    """
    return cast(
        "QuerySet[TaskResolution]",
        TaskResolution.objects.filter(task=task).order_by("-submitted_at", "-id"),
    )


def encode_resolution_cursor(resolution: TaskResolution) -> str:
    """Opaque cursor carrying the full sort key of *resolution* (rule 1)."""
    material = f"{resolution.submitted_at.isoformat()}|{resolution.pk}"
    return encode_cursor(material)


def decode_resolution_cursor(raw: str | None) -> ResolutionCursorKey | None:
    """Parse a cursor back into its sort key; ``None`` = first page.

    A cursor that does not decode into this endpoint's exact key shape
    answers ``VALIDATION_ERROR`` — cursors are opaque and a mangled one
    is a client error from the closed catalog (rule 1).
    """
    material = decode_str_cursor(raw)
    if material is None:
        return None
    parts = material.split("|")
    if len(parts) != 2:
        raise ValidationError("Invalid cursor.")
    timestamp_text, resolution_id_text = parts
    try:
        submitted_at = datetime.fromisoformat(timestamp_text)
        resolution_id = UUID(resolution_id_text)
    except ValueError as exc:
        raise ValidationError("Invalid cursor.") from exc
    return ResolutionCursorKey(submitted_at=submitted_at, resolution_id=resolution_id)


def filter_beyond_cursor(
    queryset: QuerySet[TaskResolution], cursor: ResolutionCursorKey
) -> QuerySet[TaskResolution]:
    """Keyset continuation: rows strictly *before* the cursor (newest-first)."""
    return queryset.filter(
        Q(submitted_at__lt=cursor.submitted_at)
        | Q(submitted_at=cursor.submitted_at, id__lt=cursor.resolution_id)
    )


def resolution_page(
    task: Task, *, cursor: ResolutionCursorKey | None, page_size: int
) -> tuple[list[TaskResolution], str | None]:
    """One page of *task*'s submissions plus its ``next_cursor``.

    Fetch-one-lookahead (pagination.md): ``next_cursor`` is ``None``
    exactly when the page is the last one.
    """
    queryset = resolution_list_queryset(task)
    if cursor is not None:
        queryset = filter_beyond_cursor(queryset, cursor)
    rows = list(queryset[: page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = encode_resolution_cursor(rows[-1]) if has_more and rows else None
    return rows, next_cursor


__all__ = [
    "DIFF_TOO_LARGE_MARKER",
    "PATCH_MAX_BYTES",
    "ResolutionCursorKey",
    "ResolutionSubmission",
    "assert_same_project",
    "decode_resolution_cursor",
    "encode_resolution_cursor",
    "filter_beyond_cursor",
    "patch_payload",
    "patch_storage_key",
    "resolution_list_queryset",
    "resolution_or_404",
    "resolution_page",
    "store_patch_artifact",
    "submit_resolution",
]
