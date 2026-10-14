"""MT-3.9-02 — ``review.requested`` emission on every ``in_human_review`` entry.

FR-MOB-04's backend half, wired as **one hook on the transition itself**
(never per-callsite sends): the dispatcher emits exactly one
``review.requested`` event whenever a row lands the task in
``in_human_review`` — T8 (self-flagged/scope violation), T9 (retry
exhausted), T14 (verdict escalation with the Policy Engine's persisted
rule details) today; T18 when WP-3.7 wires its row, and any fifth
entry path through the same ``to_state`` rule (MT-3.9-02 risk note).

What this suite proves:

* each entry transition writes **exactly one** entry event with the
  canonical reason — never zero, never two (the push seam stays a
  single downstream consumer, not a second writer);
* non-entry transitions emit none (T4 claim, T5 expiry, T13 pass);
* re-entry after a later cycle emits a **fresh** event (one per entry,
  not one per task);
* the event row is written in the same transaction as the Transition
  row and published strictly post-commit (Sections 8.2, 9.6).

Run with ``pytest backend/tests -k review_requested_emission -q``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.audit.policy.wiring import ensure_policy_engine_wired
from apps.projects.models import Project
from apps.tasks.models import ClaimedRole, ReviewReason, Task, TaskState, TaskTransition
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.hooks import set_review_rule_details_hook
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY
from tests.wp15_helpers import install_event_recorder, make_project, make_task, reset_hooks
from tests.wp16_helpers import restore_lease_registry  # noqa: F401  (autouse)
from tests.wp33_helpers import (  # noqa: F401  (helpers; local restore below)
    JsonAPIClient,
    agent_client,
    claim_as_auditor,
    issue_agent_token,
    login_owner_client,
)
from tests.wp34_helpers import CRITICAL_PATCH, auditable_with_patch

pytestmark = pytest.mark.django_db


@pytest.fixture
def policy_engine_installed() -> None:
    """The real wiring under test (both seams; MT-3.4-07)."""
    ensure_policy_engine_wired()


@pytest.fixture(autouse=True)
def review_registry() -> Iterator[None]:
    """Snapshot the registry; these contracts run against the ambient engine."""
    ensure_registered()
    snapshot = DEFAULT_REGISTRY.specs()
    try:
        yield
    finally:
        DEFAULT_REGISTRY.replace_all(snapshot)
        reset_hooks()
        set_review_rule_details_hook(None)


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    return login_owner_client()


@pytest.fixture
def project(db: None) -> Project:
    """One project row with the default policy."""
    return make_project(name="WP-3.9 emission")


def _reviewed(records: list[Any]) -> list[dict[str, Any]]:
    """The ``review.requested`` payloads a recorder captured."""
    return [dict(record) for record in records if record["type"] == "review.requested"]


def _make_exhausted(project: Project, index: int = 1) -> Task:
    """An ``in_progress`` row at the retry ceiling (T9's premises)."""
    task = make_task(project, index, state=TaskState.IN_PROGRESS, failure_retry_count=3)
    task.worker_agent_id = "claude-code-session-98b2"
    task.worker_session_id = "sess_7f3c91d0a2b44e"
    task.claimed_role = ClaimedRole.CODER
    task.lease_acquired_at = timezone.now()
    task.lease_expires_at = timezone.now()
    task.save()
    return task


# --- one event per entry, per transition --------------------------------------


def test_t9_entry_emits_exactly_one_event(project: Project) -> None:
    """Retry exhaustion: one entry event, one history row, one push."""
    from tests.wp15_helpers import install_push_recorder

    task = _make_exhausted(project)
    records = install_event_recorder()
    pushes = install_push_recorder()

    dispatch_transition(
        task_id=task.pk, trigger="retry_exhausted", actor_type="system", actor_ref="sweeper"
    )

    entries = _reviewed(records)
    assert len(entries) == 1
    assert entries[0]["data"]["review_reason"] == ReviewReason.RETRY_EXHAUSTED
    assert len(pushes) == 1, "push is one downstream consumer of the same entry"
    assert TaskTransition.objects.filter(task=task).count() == 1, "one transition, one entry"


def test_t8_entry_emits_exactly_one_event(owner_client: JsonAPIClient, project: Project) -> None:
    """Self-flagged submission: one entry event with the T8 reason."""
    from tests.wp32_helpers import claimed_task, submission_body

    task = claimed_task(project, 1)
    coder = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    records = install_event_recorder()

    submission = coder.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(requires_human_attention=True, risk_justification="flagged"),
        format="json",
    )
    assert submission.status_code == 201, submission.content
    task.refresh_from_db()

    entries = _reviewed(records)
    assert len(entries) == 1
    # T8's Section 8.2 pair — whichever the submission's shape hit.
    assert task.review_reason in {ReviewReason.SELF_FLAGGED, ReviewReason.SCOPE_VIOLATION}
    assert entries[0]["data"]["review_reason"] == task.review_reason


def test_t14_entry_emits_exactly_one_event_with_rule_details(
    owner_client: JsonAPIClient, project: Project, policy_engine_installed: None
) -> None:
    """Verdict escalation: one entry event; the rule details ride along."""
    # In-scope critical-path change: R2 passes, R3 fails (first reason).
    task = auditable_with_patch(project, 1, patch=CRITICAL_PATCH, target_scope=(".github/**",))
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    assert claim_as_auditor(auditor, task.pk).status_code == 200
    records = install_event_recorder()

    verdict = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        {
            "session_id": "sess_wp33_auditor",
            "lease_generation": 1,
            "task_id": task.pk,
            "verdict": "pass",
            "confidence": 4,
            "notes": "",
            "evidence": {"commands": [{"label": "tests", "command": "pytest -q", "exit_code": 0}]},
        },
        format="json",
    )
    assert verdict.status_code == 201, verdict.content

    entries = _reviewed(records)
    assert len(entries) == 1, "exactly one per entry, despite the audit.escalated row event"
    data = entries[0]["data"]
    assert data["review_reason"] == ReviewReason.CRITICAL_PATH_CHANGED
    assert data["policy_rule_results"], "T14 carries the persisted engine results"


# --- non-entry transitions and re-entry ---------------------------------------


def test_non_entry_transitions_emit_no_review_requested(project: Project) -> None:
    """T5's expiry return to pending is not an entry — no event, no push."""
    from tests.wp15_helpers import install_push_recorder

    task = _make_exhausted(project, 1)
    # A second in the past, not ``now``: the T5 guard is strictly
    # ``lease_expires_at < now``, and an equal timestamp loses to a coarse
    # clock tick (the full-suite run under load flaked on the boundary).
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    records = install_event_recorder()
    pushes = install_push_recorder()

    dispatch_transition(
        task_id=task.pk, trigger="lease_expired", actor_type="system", actor_ref="sweeper"
    )

    assert [record["type"] for record in records] == ["task.lease_expired"]
    assert _reviewed(records) == [], "T5 is not an in_human_review entry"
    assert pushes == []


def test_t13_pass_branch_emits_no_review_requested(
    owner_client: JsonAPIClient, project: Project, policy_engine_installed: None
) -> None:
    """The pass half of the verdict row stays quiet (merge pending, no entry)."""
    task = auditable_with_patch(project, 4)  # CLEAN_PATCH: every rule passes
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    assert claim_as_auditor(auditor, task.pk).status_code == 200
    records = install_event_recorder()

    verdict = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        {
            "session_id": "sess_wp33_auditor",
            "lease_generation": 1,
            "task_id": task.pk,
            "verdict": "pass",
            "confidence": 5,
            "notes": "",
            "evidence": {"commands": [{"label": "tests", "command": "pytest -q", "exit_code": 0}]},
        },
        format="json",
    )
    assert verdict.status_code == 201, verdict.content
    task.refresh_from_db()
    assert task.state == TaskState.TO_BE_AUDITED, "T13 merge-pending sub-status"
    assert _reviewed(records) == [], "no entry, no review.requested"


def test_reentry_after_a_later_cycle_emits_a_fresh_event(project: Project) -> None:
    """One per entry, not one per task: a second cycle emits again."""
    from apps.audit.review import ensure_review_wired

    first = _make_exhausted(project, 1)
    records = install_event_recorder()
    dispatch_transition(
        task_id=first.pk, trigger="retry_exhausted", actor_type="system", actor_ref="sweeper"
    )
    assert len(_reviewed(records)) == 1

    # The owner sends it back (T16), the coder claims again (a
    # claim-shaped seed — the T4 columns), and the retries exhaust once
    # more (T9) — a fresh entry on the same task.
    ensure_review_wired()
    dispatch_transition(
        task_id=first.pk,
        trigger="request_changes",
        actor_type="owner",
        actor_ref="owner-1",
        note="try a smaller slice",
        extra={
            "resolution": None,
            "note": "try a smaller slice",
            "decided_by": "owner-1",
            "decided_via": "web",
        },
    )
    second_cycle = Task.objects.get(pk=first.pk)
    assert second_cycle.state == TaskState.PENDING
    second_cycle.state = TaskState.IN_PROGRESS
    second_cycle.worker_agent_id = "claude-code-session-98b2"
    second_cycle.worker_session_id = "sess_7f3c91d0a2b44e"
    second_cycle.claimed_role = ClaimedRole.CODER
    second_cycle.lease_acquired_at = timezone.now()
    second_cycle.lease_expires_at = timezone.now()
    second_cycle.failure_retry_count = 3
    second_cycle.save()
    dispatch_transition(
        task_id=second_cycle.pk,
        trigger="retry_exhausted",
        actor_type="system",
        actor_ref="sweeper",
    )

    entries = _reviewed(records)
    assert len(entries) == 2, "one per entry (MT-3.9-02: never one per task)"


# --- same transaction, post-commit publication --------------------------------


def test_entry_event_is_written_in_the_transition_transaction(
    project: Project, django_capture_on_commit_callbacks: Any, monkeypatch: Any
) -> None:
    """In-atomic write (8.2 rule 2), publish strictly post-commit (9.6)."""
    from apps.events.models import Event

    published: list[str] = []
    import apps.events.services as events_services

    monkeypatch.setattr(
        events_services, "publish_event", lambda event: published.append(event.type)
    )
    task = _make_exhausted(project)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        dispatch_transition(
            task_id=task.pk,
            trigger="retry_exhausted",
            actor_type="system",
            actor_ref="sweeper",
        )
        # The production writer (no recorder override here) wrote the row
        # inside the open transaction — the same block as the Transition
        # row — and deferred every publish to commit.
        assert Event.objects.filter(task_id=task.pk, type="review.requested").exists()
        assert published == [], "nothing publishes while the transaction is open"

    # Post-commit: both events of the dispatch reached the publisher.
    assert callbacks, "the writer registered post-commit publishes"
    assert published.count("review.requested") == 1, "published once, after commit"
    assert published.count("task.transitioned") == 1
