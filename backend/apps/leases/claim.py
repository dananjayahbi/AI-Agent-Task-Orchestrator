"""The atomic claim transaction and next-available selection (Sections 9.3, 8.6).

Implements Section 9.3 step for step:

1. **Project from the token** — the caller passes only what its agent
   token proved (``caller_project_id``); the request body never names a
   project (ADR-004; G-07). The service answers
   ``AUTH_FORBIDDEN_PROJECT`` before any write if the locked row belongs
   elsewhere.
2. **One transaction** wraps lock, re-validation and dispatch.
3. **Exclusive, skip-locked row lock** —
   ``SELECT … FOR UPDATE SKIP LOCKED`` on the target id. No row
   returned → the cheap follow-up read of the same statement set:
   the row *exists* (another transaction holds it mid-claim) →
   ``TASK_ALREADY_CLAIMED``; it does not → ``TASK_NOT_FOUND``.
4. **Re-validate inside the lock** — state ``pending`` (the dispatch
   resolve answers ``TASK_STATE_CONFLICT`` for every other from-state,
   while ``in_progress`` answers ``TASK_ALREADY_CLAIMED``: held by a
   worker until the sweeper's T5, Section 8.6), then the T4 guard row:
   scope, project active, dependencies, concurrency (``wiring``).
5. **Lease write + fencing** — the T4 side effect sets worker, session,
   role, acquire/expire timestamps from Project Policy, and increments
   ``lease_generation`` and ``attempt_number``; the dispatcher commits
   state, version, Transition and the ``task.claimed`` event hook
   together.
6. **Return** the task; the view renders task details, the Section 8.6
   lease record and the Section 10.6 rules block from it.

"Next available" (Section 9.3 last paragraph) reuses the same lock and
ordering on a *candidate set*: the canonical FR-TSK-05 order
(``task_list_queryset`` — priority then ``created_at`` then generation
order), eligibility filters, then ``FOR UPDATE SKIP LOCKED … LIMIT 1``
so two concurrent selectors receive different tasks with no coordinator.

Clock: ``django.utils.timezone.now()`` via the T4 side effect — one
documented source (MT-1.6-03 risk note).
"""

from __future__ import annotations

from typing import Literal

from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet
from rest_framework.exceptions import ValidationError

from apps.accounts.exceptions import AuthForbiddenProject
from apps.audit.transitions import ensure_audit_wired
from apps.projects.models import Project
from apps.tasks.exceptions import TaskNotFound
from apps.tasks.models import Task, TaskDependency, TaskState
from apps.tasks.services.ids import ensure_valid_task_id
from apps.tasks.services.tasks import task_list_queryset
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .exceptions import RoleNotAllowed, TaskAlreadyClaimed
from .wiring import claim_extra, ensure_wired

WorkRole = Literal["coder", "auditor"]


def _require_identity(*, session_id: str, worker_agent_id: str) -> None:
    """Claim identity is part of the FR-LEA-02 record — blank is a client error."""
    errors: dict[str, str] = {}
    if not session_id.strip():
        errors["session_id"] = "This field is required and may not be blank."
    if not worker_agent_id.strip():
        errors["worker_agent_id"] = "This field is required and may not be blank."
    if errors:
        raise ValidationError(errors)


def eligible_work_queryset(
    project: Project,
    *,
    role: WorkRole,
    priority: str | None = None,
) -> QuerySet[Task]:
    """Offerable tasks for *role* (FR-PRJ-04, FR-TSK-07; non-locking read).

    ``coder`` → ``pending``; ``auditor`` → ``to_be_audited`` (T11's
    audit claim takes the matching half — this list is the Section 9.2
    ``GET /projects/{pid}/work`` read path, MT-3.3-01). Archived rows are hidden
    (T19 default), dependencies must be completed (one ``EXISTS``
    negation — the same readiness semantics as
    ``services.dependencies.all_dependencies_completed``), and callers
    return an empty result for a non-active project (FR-PRJ-04).
    ``priority`` is the Section 9.2 "filters" parameter this MT surfaces
    (a *state* filter would contradict "available" — the offer list's
    states are exactly the role's; MT-1.6-02's recorded reading).
    """
    states: tuple[str, ...] = (
        (TaskState.PENDING,) if role == "coder" else (TaskState.TO_BE_AUDITED,)
    )
    queryset = task_list_queryset(project, states=states, priority=priority)
    unmet = TaskDependency.objects.filter(task_id=OuterRef("pk")).exclude(
        depends_on__state=TaskState.COMPLETED
    )
    return queryset.exclude(Exists(unmet))


def claim_task(
    *,
    task_id: str,
    session_id: str,
    worker_agent_id: str,
    caller_project_id: str | None,
    role: WorkRole = "coder",
) -> Task:
    """Claim *task_id* per Section 9.3; return the claimed (locked) row.

    ``role`` is the Section 10.5 ``claim_task`` input (coder default):
    **request intent only** — it is validated against the row's state
    inside the lock (Section 12.2: claim ``pending`` is coder-only, claim
    ``to_be_audited`` is auditor-only), while the *token's scopes* answer
    first at the permission gate (roles via token scopes; the parameter
    is never trusted — MT-3.3-01 risk note). ``coder`` dispatches T4,
    ``auditor`` dispatches T11 (whose guards carry the G-20 independence
    rule and the audit-lease check); a role that mismatches the two
    claimable states answers ``ROLE_NOT_PERMITTED``, any other
    from-state answers the registry's ``TASK_STATE_CONFLICT``.

    Exactly one claimant can win: on Postgres the skip-locked lock makes
    every other concurrent caller either fast-fail on the follow-up read
    (``TASK_ALREADY_CLAIMED``) or observe the committed ``in_progress``
    state (same code); the unit layer's SQLite runs the identical logic
    with the single-writer table lock (Section 18 layering — the 50-way
    race proof lives on real Postgres in ``tests/integration``).
    """
    ensure_valid_task_id(task_id)
    _require_identity(session_id=session_id, worker_agent_id=worker_agent_id)
    if role not in ("coder", "auditor"):
        raise ValueError(f"role {role!r} must be 'coder' or 'auditor' (Section 10.5)")
    if caller_project_id is None:
        # Agent tokens always carry a project (WP-1.2); fail closed rather
        # than offer rows nobody proved they may see (ADR-004).
        raise AuthForbiddenProject("Agent token carries no project scope.")
    ensure_wired()

    with transaction.atomic():
        task = Task.objects.select_for_update(skip_locked=True).filter(pk=task_id).first()
        if task is None:
            # Section 9.3 step 3: the cheap follow-up read distinguishes
            # "held by a racing claimant" from "does not exist".
            if Task.objects.filter(pk=task_id).exists():
                raise TaskAlreadyClaimed(task_id)
            raise TaskNotFound(f"Task {task_id} does not exist.")
        if task.project_id != caller_project_id:
            raise AuthForbiddenProject(
                f"Token is scoped to {caller_project_id!r}, not {task.project_id!r}."
            )
        if task.state == TaskState.IN_PROGRESS:
            # Held — including expired-but-unswept: reclamation is T5's job
            # (Section 8.6), never a second claimant's.
            raise TaskAlreadyClaimed(task_id, holder=task.worker_agent_id)
        # MT-3.3-01: the Section 12.2 claim cells, checked against the
        # *declared* role before dispatch — the other role's claimable
        # state is a role refusal (403); every remaining state falls to
        # the registry's TASK_STATE_CONFLICT (the dispatch resolve).
        claimable: dict[str, str] = {TaskState.PENDING: "coder", TaskState.TO_BE_AUDITED: "auditor"}
        if task.state in claimable and claimable[task.state] != role:
            raise RoleNotAllowed(task_id, role=role, state=task.state)
        if role == "auditor":
            ensure_audit_wired()  # T11's row (lazy wiring, MT-1.5-04 seam)
        return dispatch_transition(
            task_id=task.pk,
            trigger="claim" if role == "coder" else "audit_claim",
            actor_type="agent",
            actor_ref=session_id,
            extra=claim_extra(
                caller_project_id=caller_project_id,
                session_id=session_id,
                worker_agent_id=worker_agent_id,
            ),
        )


def claim_next_available(
    *,
    caller_project_id: str | None,
    session_id: str,
    worker_agent_id: str,
) -> Task | None:
    """Select and claim the next offerable task (Section 9.3 last paragraph).

    ``None`` means no eligible task right now — an empty result, never an
    error (the bridge maps it to its no-work response; FR-PRJ-04's paused
    project answers the same way). Concurrent selectors skip each other's
    locked rows, so two agents asking simultaneously receive different
    tasks automatically.
    """
    _require_identity(session_id=session_id, worker_agent_id=worker_agent_id)
    if caller_project_id is None:
        raise AuthForbiddenProject("Agent token carries no project scope.")
    project = Project.objects.filter(pk=caller_project_id).select_related("agent_policy").first()
    if project is None or project.active_status != "active":
        return None  # FR-PRJ-04: a non-active project offers no work
    ensure_wired()

    with transaction.atomic():
        candidate = (
            eligible_work_queryset(project, role="coder")
            .select_for_update(skip_locked=True)
            .first()
        )
        if candidate is None:
            return None
        return dispatch_transition(
            task_id=candidate.pk,
            trigger="claim",
            actor_type="agent",
            actor_ref=session_id,
            extra=claim_extra(
                caller_project_id=caller_project_id,
                session_id=session_id,
                worker_agent_id=worker_agent_id,
            ),
        )
