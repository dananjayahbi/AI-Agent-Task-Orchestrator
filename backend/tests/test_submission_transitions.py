"""MT-3.2-05 — submission transitions T7/T8/T10 (Sections 8.2/8.4/8.5/19).

Run with ``pytest backend/tests -k submission_transitions -q``. The
Section 19 WP-3.2 acceptance cases run through the real endpoint; guard
refusals run through the dispatcher directly (the wiring contract):

* **T7** clean submission → ``to_be_audited``: one Transition row with
  the actor recorded, one ``task.transitioned`` Event row, worker
  cleared, no push (Section 8.2 side effects; FR-TSK-04);
* **T8** self-flag → ``in_human_review`` + ``self_flagged`` (Section
  8.4 verbatim) with the Section 9.8 push; out-of-scope →
  ``in_human_review`` + ``scope_violation`` with the offending paths
  captured; **precedence** (recorded): scope wins when both hold;
* **T10** ``audit_required`` false → the engine seam, fail-closed:
  without the WP-3.4 hook the submission escalates to
  ``in_human_review`` with an enumerated Section 8.4 reason and **never**
  approves; with an approving hook it lands merge-pending
  (``merge_status = pending`` on ``to_be_audited``) — approve is
  reachable only through the seam (invariant 8.3.4), and each row
  re-consults it so a forged trigger cannot bypass the engine;
* refusals: wrong-from-state and wrong-trigger pairs answer
  ``TASK_STATE_CONFLICT`` (409), the wrong actor
  ``ROLE_NOT_PERMITTED`` (403), T7's five guards and T8's one refuse
  with catalog codes only (including ``SCOPE_VIOLATION``), and every
  emitted event type stays inside the Section 9.6 catalog (20.4 item 6).
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from rest_framework.test import APIClient

from apps.core.errors import ROLE_NOT_PERMITTED, TASK_STATE_CONFLICT
from apps.events.models import Event
from apps.projects.models import Project
from apps.tasks.exceptions import (
    ScopeViolation,
    TaskStateConflict,
    TransitionActorForbidden,
    TransitionNotWired,
)
from apps.tasks.models import Task, TaskResolution, TaskState, TaskTransition
from apps.tasks.services.scope import ScopeVerdict
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.transitions_agent import T8_REVIEW_REASONS
from apps.tasks.state_machine.transitions_submission import (
    PolicyDecision,
    ensure_submission_wired,
    resolve_policy_decision,
    set_policy_decision_hook,
)

from .wp15_helpers import SECTION_9_6_EVENTS, install_push_recorder
from .wp32_helpers import (  # noqa: F401  (autouse fixtures promoted)
    _code,
    active_policy_project,
    agent_client,
    claimed_task,
    install_event_recorder,
    issue_agent_token,
    local_storage,
    login_owner,
    restore_submission_registry,
    submission_body,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (cookie transport) for token minting."""
    return login_owner()


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


def _coder(owner_client: APIClient, project: Project) -> APIClient:
    return agent_client(issue_agent_token(owner_client, project.pk, "coder"))


def _submit(client: APIClient, task: Task, **overrides: Any) -> Any:
    return client.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(**overrides),
        format="json",
    )


def _resolution_for(task: Task, **overrides: Any) -> TaskResolution:
    """A stored resolution row for direct dispatch (one per fresh test)."""
    payload: dict[str, Any] = {
        "task": task,
        "attempt_number": task.attempt_number,
        "branch_name": "feat/direct",
        "commit_sha": "d" * 40,
        "execution_summary": "direct dispatch",
    }
    payload.update(overrides)
    return cast(TaskResolution, TaskResolution.objects.create(**payload))


def _dispatch(
    task: Task,
    trigger: str,
    resolution: TaskResolution,
    verdict: ScopeVerdict,
    *,
    actor_type: str = "agent",
    session_id: str = "sess_wp32",
    lease_generation: int = 1,
) -> Task:
    """One guarded dispatch through the public extension-point rows."""
    ensure_submission_wired()
    return dispatch_transition(
        task_id=task.pk,
        trigger=trigger,
        actor_type=actor_type,
        actor_ref=session_id,
        extra={
            "session_id": session_id,
            "lease_generation": lease_generation,
            "resolution": resolution,
            "scope_verdict": verdict,
        },
    )


# --- T7: the clean path (Section 19 acceptance, positive half) ---------------


def test_t7_clean_submission_lands_to_be_audited_with_one_of_each_row(
    owner_client: APIClient, project: Project
) -> None:
    """Store resolution + patch, clear worker: Transition + Event in one tx."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    response = _submit(agent, task)

    assert response.status_code == 201, response.content
    assert response.json()["task"]["state"] == "to_be_audited"
    fresh = Task.objects.get(pk=task.pk)
    assert fresh.state == TaskState.TO_BE_AUDITED
    assert fresh.worker_agent_id is None and fresh.claimed_role is None

    row = TaskTransition.objects.get(task=task, from_state="in_progress")
    assert (row.to_state, row.actor_type, row.actor_ref) == (
        "to_be_audited",
        "agent",
        "sess_wp32",
    )
    assert row.reason_code == "submit"
    assert row.note == ""

    event = Event.objects.get(type="task.transitioned", task_id=task.pk)
    assert event.data["to_state"] == "to_be_audited"
    assert event.data["reason_code"] == "submit"


# --- T8: the Section 19 acceptance cases -------------------------------------


def test_self_flagged_submission_lands_in_human_review_with_self_flagged(
    owner_client: APIClient, project: Project
) -> None:
    """Section 19: self-flagged submission → review with ``self_flagged``."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])
    pushes = install_push_recorder()

    response = _submit(agent, task, requires_human_attention=True)

    assert response.status_code == 201, response.content
    assert response.json()["task"]["state"] == "in_human_review"
    assert response.json()["task"]["review_reason"] == "self_flagged"
    assert response.json()["trigger"] == "submit_flagged"
    fresh = Task.objects.get(pk=task.pk)
    assert fresh.review_reason == "self_flagged"
    assert fresh.worker_session_id is None
    assert len(pushes) == 1, "Section 9.8: in_human_review entry triggers push"
    assert pushes[0]["reason_code"] == "self_flagged"


def test_out_of_scope_submission_lands_with_scope_violation(
    owner_client: APIClient, project: Project
) -> None:
    """Section 19: out-of-scope patch → review with ``scope_violation``."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**"])  # docs/ is outside
    pushes = install_push_recorder()

    response = _submit(agent, task)

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["task"]["state"] == "in_human_review"
    assert body["task"]["review_reason"] == "scope_violation"
    assert body["scope_violations"] == ["docs/readme.md"], "offending path captured"
    assert Task.objects.get(pk=task.pk).review_reason == "scope_violation"
    assert len(pushes) == 1
    row = TaskTransition.objects.get(task=task, from_state="in_progress")
    assert row.reason_code == "scope_violation"
    assert "docs/readme.md" in row.note


def test_scope_violation_beats_self_flagged_when_both_hold(
    owner_client: APIClient, project: Project
) -> None:
    """Recorded precedence (MT-3.2-05 risk note): scope wins; the pair stays strict."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**"])

    response = _submit(agent, task, requires_human_attention=True)

    assert response.status_code == 201
    assert response.json()["task"]["review_reason"] == "scope_violation"
    assert set(T8_REVIEW_REASONS) == {"self_flagged", "scope_violation"}


# --- the guard cells, through the dispatcher ---------------------------------


def test_t7_guard_refuses_audit_required_false(owner_client: APIClient, project: Project) -> None:
    """ "audit_required true" — T10's row owns that branch (409)."""
    task = claimed_task(project, 1, target_scope=["src/**"], audit_required=False)
    resolution = _resolution_for(task)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "submit", resolution, ScopeVerdict(violations=()))

    assert caught.value.default_code == TASK_STATE_CONFLICT
    assert Task.objects.get(pk=task.pk).state == TaskState.IN_PROGRESS, "rolled back"


def test_t7_guard_refuses_a_self_flagged_resolution(
    owner_client: APIClient, project: Project
) -> None:
    """ "not self-flagged" — a flagged submission must take T8 (409)."""
    task = claimed_task(project, 1, target_scope=["src/**"])
    resolution = _resolution_for(task, requires_human_attention=True)

    with pytest.raises(TaskStateConflict):
        _dispatch(task, "submit", resolution, ScopeVerdict(violations=()))


def test_t7_guard_refuses_out_of_scope_with_the_catalog_code(
    owner_client: APIClient, project: Project
) -> None:
    """ "scope check ok" — the catalog SCOPE_VIOLATION, no new code (409)."""
    task = claimed_task(project, 1, target_scope=["src/**"])
    resolution = _resolution_for(task)

    with pytest.raises(ScopeViolation) as caught:
        _dispatch(
            task,
            "submit",
            resolution,
            ScopeVerdict(violations=("docs/readme.md",)),
        )

    assert caught.value.default_code == "SCOPE_VIOLATION"
    assert caught.value.status_code == 409


def test_t7_guard_refuses_a_resolution_from_another_attempt(
    owner_client: APIClient, project: Project
) -> None:
    """ "resolution valid" — attempt linkage is checked, not assumed (409)."""
    task = claimed_task(project, 1, target_scope=["src/**"])
    resolution = _resolution_for(task, attempt_number=task.attempt_number + 7)

    with pytest.raises(TaskStateConflict):
        _dispatch(task, "submit", resolution, ScopeVerdict(violations=()))


def test_t8_guard_needs_a_flag_or_a_violation(owner_client: APIClient, project: Project) -> None:
    """T8's cell verbatim: neither condition answers TASK_STATE_CONFLICT."""
    task = claimed_task(project, 1, target_scope=["src/**"])
    resolution = _resolution_for(task)

    with pytest.raises(TaskStateConflict):
        _dispatch(task, "submit_flagged", resolution, ScopeVerdict(violations=()))


def test_illegal_pairs_and_wrong_actors_use_the_catalog(
    owner_client: APIClient, project: Project
) -> None:
    """Unmapped pair → TASK_STATE_CONFLICT; wrong actor → ROLE_NOT_PERMITTED."""
    from apps.tasks.state_machine.loader import ensure_registered

    ensure_registered()
    ensure_submission_wired()
    task = claimed_task(project, 1, target_scope=["src/**"])
    resolution = _resolution_for(task)

    # submit from a state the table does not map (registry rule 1).
    Task.objects.filter(pk=task.pk).update(state=TaskState.PENDING)
    pending = Task.objects.get(pk=task.pk)
    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(pending, "submit", resolution, ScopeVerdict(violations=()))
    assert caught.value.default_code == TASK_STATE_CONFLICT

    # back to in_progress: the actor column refuses the owner.
    Task.objects.filter(pk=task.pk).update(state=TaskState.IN_PROGRESS)
    held = Task.objects.get(pk=task.pk)
    with pytest.raises(TransitionActorForbidden) as forbidden:
        _dispatch(
            held,
            "submit",
            resolution,
            ScopeVerdict(violations=()),
            actor_type="owner",
        )
    assert forbidden.value.default_code == ROLE_NOT_PERMITTED
    assert forbidden.value.status_code == 403


def test_emitted_event_types_stay_in_the_section_9_6_catalog(
    owner_client: APIClient, project: Project
) -> None:
    """20.4 item 6: T7/T8/T10 all emit ``task.transitioned`` (already cataloged)."""
    agent = _coder(owner_client, project)
    clean = claimed_task(project, 1, target_scope=["src/**", "docs/**"])
    _submit(agent, clean)
    flagged = claimed_task(project, 2, target_scope=["src/**", "docs/**"])
    _submit(agent, flagged, requires_human_attention=True)

    events = Event.objects.filter(task_id__in=[clean.pk, flagged.pk], type="task.transitioned")
    assert events.count() == 2
    for event in events:
        assert event.type in SECTION_9_6_EVENTS


# --- T10: the policy seam (Section 8.5; invariant 8.3.4) ---------------------


def test_t10_escalates_fail_closed_without_the_engine(
    owner_client: APIClient, project: Project
) -> None:
    """audit_required false, no engine: escalate, never approve (recorded)."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"], audit_required=False)
    pushes = install_push_recorder()

    response = _submit(agent, task)

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["trigger"] == "submit_unreviewed"
    assert body["task"]["state"] == "in_human_review"
    assert body["task"]["review_reason"] == "policy_forced_review"
    assert body["task"]["merge_status"] == "none", "never auto-approved"
    fresh = Task.objects.get(pk=task.pk)
    assert fresh.state == TaskState.IN_HUMAN_REVIEW
    assert fresh.merge_status == "none"
    assert len(pushes) == 1, "escalation is a push-triggering review entry"


def test_t10_approve_branch_is_reachable_only_through_the_seam(
    owner_client: APIClient, project: Project
) -> None:
    """With an approving engine: merge-pending (pending on to_be_audited)."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"], audit_required=False)
    set_policy_decision_hook(lambda _task, _resolution, _verdict: PolicyDecision(approve=True))

    response = _submit(agent, task)

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["trigger"] == "submit_policy_approved"
    assert body["task"]["state"] == "to_be_audited", "T13's merge-pending reading"
    assert body["task"]["merge_status"] == "pending"
    assert body["task"]["review_reason"] is None
    fresh = Task.objects.get(pk=task.pk)
    assert fresh.merge_status == "pending"
    assert fresh.worker_session_id is None


def test_t10_approve_row_refuses_when_the_engine_has_not_approved(
    owner_client: APIClient, project: Project
) -> None:
    """A forged trigger cannot bypass the seam (invariant 8.3.4, structural)."""
    task = claimed_task(project, 1, target_scope=["src/**"], audit_required=False)
    resolution = _resolution_for(task)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "submit_policy_approved", resolution, ScopeVerdict(violations=()))

    assert "policy engine has not approved" in str(caught.value)
    fresh = Task.objects.get(pk=task.pk)
    assert fresh.merge_status == "none"
    assert fresh.state == TaskState.IN_PROGRESS, "rolled back"


def test_t10_escalate_row_refuses_when_the_engine_approved(
    owner_client: APIClient, project: Project
) -> None:
    """Symmetric: an approving engine forbids the escalation branch."""
    task = claimed_task(project, 1, target_scope=["src/**"], audit_required=False)
    resolution = _resolution_for(task)
    set_policy_decision_hook(lambda _task, _resolution, _verdict: PolicyDecision(approve=True))

    with pytest.raises(TaskStateConflict):
        _dispatch(task, "submit_unreviewed", resolution, ScopeVerdict(violations=()))


def test_policy_seam_escalation_reason_must_be_a_section_8_4_member(
    owner_client: APIClient, project: Project
) -> None:
    """Catalog-first: a free-text reason from the hook is a programming error."""
    task = claimed_task(project, 1, target_scope=["src/**"], audit_required=False)
    resolution = _resolution_for(task)
    verdict = ScopeVerdict(violations=())
    set_policy_decision_hook(
        lambda _task, _resolution, _verdict: PolicyDecision(
            approve=False, reason="not_a_canonical_reason"
        )
    )

    with pytest.raises(ValueError, match="Section 8.4"):
        resolve_policy_decision(task, resolution, verdict)


def test_t10_structural_guards_match_t7s_cleanliness(
    owner_client: APIClient, project: Project
) -> None:
    """audit_required true, a flag, or scope dirt all refuse T10's rows."""
    task = claimed_task(project, 1, target_scope=["src/**"])  # docs/ outside
    resolution = _resolution_for(task)

    with pytest.raises(TaskStateConflict):  # audit_required is true by default
        _dispatch(task, "submit_unreviewed", resolution, ScopeVerdict(violations=()))


def test_stub_registry_restores_between_tests(owner_client: APIClient, project: Project) -> None:
    """The wp32 restore fixture keeps the loader's stub rows visible again."""
    from apps.tasks.state_machine.loader import ensure_registered
    from apps.tasks.state_machine.registry import DEFAULT_REGISTRY

    ensure_registered()
    submit_row = DEFAULT_REGISTRY.get("submit")
    assert submit_row is not None and submit_row.wired is False, "loader stub"
    task = claimed_task(project, 1, target_scope=["src/**"])
    with pytest.raises(TransitionNotWired):
        dispatch_transition(
            task_id=task.pk,
            trigger="submit",
            actor_type="agent",
            actor_ref="sess_wp32",
            extra={},
        )
