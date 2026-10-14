"""MT-3.9-01 — the ``review.requested`` payload contract (Section 9.6 envelope).

The contract the plan derives but does not field-pin (MT-3.9-01 risk
note — fields come from Sections 9.4, 8.4 and the 9.8 dedupe key only):

* the **envelope** is Section 9.6 verbatim: ``type`` =
  ``review.requested`` (a §9.6 catalog member — 20.4 item 6), plus
  ``project_id``, ``task_id``, ``occurred_at`` and ``actor``;
* ``data`` carries the canonical ``review_reason`` (the Section 8.4
  enum — 12 values, none invented), ``task_version`` (the §9.8 dedupe
  key ``(event type, task id, state version)`` needs it), and — only
  where the Policy Engine decided (T14) — the **persisted**
  ``policy_rule_results`` whose structure is WP-3.4's exact
  per-rule shape (``{rule, passed, review_reason}`` per row — one
  vocabulary, never a parallel "escalation details" shape);
* ``data`` never carries free-text evidence or secrets (Section 9.8
  payload minimization — the keys are a closed set the assertions
  below pin).

Run with ``pytest backend/tests -k review_requested_payload -q``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from django.utils import timezone

from apps.audit.models import AuditReport
from apps.audit.policy.wiring import ensure_policy_engine_wired
from apps.events.catalog import EVENT_TYPES
from apps.projects.models import Project
from apps.tasks.models import ClaimedRole, ReviewReason, Task, TaskState
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.hooks import (
    set_review_rule_details_hook,
)
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY, TransitionSpec
from tests.wp15_helpers import install_event_recorder, make_project, make_task, reset_hooks
from tests.wp16_helpers import restore_lease_registry  # noqa: F401  (autouse)
from tests.wp33_helpers import (  # noqa: F401  (helpers; local restore below)
    JsonAPIClient,
    agent_client,
    auditable_task,
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


#: The closed ``data`` key set MT-3.9-01 defines — anything else is drift.
DATA_KEYS = frozenset({"review_reason", "task_version", "policy_rule_results"})

#: The WP-3.4 per-rule shape (Section 7.2 ``policy_rule_results``).
RULE_ROW_KEYS = frozenset({"rule", "passed", "review_reason"})


@pytest.fixture(autouse=True)
def review_registry() -> Iterator[None]:
    """Snapshot the registry around suites that trigger the wiring WPs.

    The wp33 fixture resets the decision hooks to fail-closed; these
    contracts run against the **ambient engine** (AuditConfig.ready),
    so only the registry is restored here.
    """
    ensure_registered()
    snapshot = DEFAULT_REGISTRY.specs()
    try:
        yield
    finally:
        DEFAULT_REGISTRY.replace_all(snapshot)
        reset_hooks()
        set_review_rule_details_hook(None)  # clear any test override


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    return login_owner_client()


@pytest.fixture
def project(db: None) -> Project:
    """One project row with the default policy."""
    return make_project(name="WP-3.9 payload")


def _entry_events(records: list[Any]) -> list[dict[str, Any]]:
    """The ``review.requested`` payloads a recorder captured."""
    return [dict(record) for record in records if record["type"] == "review.requested"]


# --- envelope + plain-reason payload (T9 — no policy evaluation) -------------


def test_retry_exhaustion_envelope_and_data_contract(project: Project) -> None:
    """T9 entry: Section 9.6 envelope + {review_reason, task_version} only."""
    task = make_task(project, 1, state=TaskState.IN_PROGRESS, failure_retry_count=3)
    task.worker_agent_id = "claude-code-session-98b2"
    task.worker_session_id = "sess_7f3c91d0a2b44e"
    task.claimed_role = ClaimedRole.CODER
    task.lease_acquired_at = timezone.now()
    task.lease_expires_at = timezone.now()
    task.save()

    records = install_event_recorder()
    dispatch_transition(
        task_id=task.pk,
        trigger="retry_exhausted",
        actor_type="system",
        actor_ref="lease-sweeper",
    )

    entries = _entry_events(records)
    assert len(entries) == 1, "exactly one review.requested per entry (MT-3.9-02)"
    entry = entries[0]

    # Section 9.6 envelope, verbatim.
    assert entry["type"] == "review.requested"
    assert entry["type"] in EVENT_TYPES, "catalog membership (20.4 item 6)"
    assert entry["project_id"] == project.pk
    assert entry["task_id"] == task.pk
    assert entry["occurred_at"] is not None
    assert entry["actor"] == {"type": "system", "ref": "lease-sweeper"}

    # MT-3.9-01 data contract: reason + dedupe version, nothing else.
    assert set(entry["data"]) == {"review_reason", "task_version"}
    assert entry["data"]["review_reason"] == "retry_exhausted"
    assert entry["data"]["review_reason"] in set(ReviewReason.values), "Section 8.4 enum"
    assert entry["data"]["task_version"] == 2


# --- T14: the rule-details half (WP-3.4's persisted shape) -------------------


def test_t14_entry_carries_the_persisted_rule_details(
    owner_client: JsonAPIClient, project: Project, policy_engine_installed: None
) -> None:
    """T14 entry: data.policy_rule_results equals the persisted row, shape and all."""
    # In-scope critical-path change: R2 (scope) passes, R3 fails — the
    # escalation reason is the first failing rule in Section 9.4 order.
    task = auditable_with_patch(project, 1, patch=CRITICAL_PATCH, target_scope=(".github/**",))
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    claimed = claim_as_auditor(auditor, task.pk)
    assert claimed.status_code == 200, claimed.content

    records = install_event_recorder()
    verdict = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        {
            "session_id": "sess_wp33_auditor",
            "lease_generation": 1,
            "task_id": task.pk,
            "verdict": "pass",
            "confidence": 4,
            "notes": "looks fine to me",
            "evidence": {"commands": [{"label": "tests", "command": "pytest -q", "exit_code": 0}]},
        },
        format="json",
    )
    assert verdict.status_code == 201, verdict.content

    task.refresh_from_db()
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.review_reason == "critical_path_changed", "R3 — first failing rule"

    entries = _entry_events(records)
    assert len(entries) == 1
    data = entries[0]["data"]
    assert data["review_reason"] == "critical_path_changed"
    assert data["review_reason"] in set(ReviewReason.values)
    assert data["task_version"] == task.version

    report = AuditReport.objects.get(task=task)
    assert report.policy_rule_results is not None, "MT-3.4-06 persisted in this transaction"
    assert data["policy_rule_results"] == report.policy_rule_results, (
        "one vocabulary: the event carries WP-3.4's persisted shape, verbatim"
    )
    assert len(data["policy_rule_results"]) == 9, "every rule R1-R9, never short-circuited"
    for row in data["policy_rule_results"]:
        assert set(row) == RULE_ROW_KEYS
        assert row["rule"].startswith("R")
        assert isinstance(row["passed"], bool)
    assert any(row["rule"] == "R3" and not row["passed"] for row in data["policy_rule_results"])


# --- absence is expressible (T8/T9/T18 carry no rule results) ----------------


def test_t8_entry_names_its_reason_without_rule_results(
    owner_client: JsonAPIClient, project: Project, policy_engine_installed: None
) -> None:
    """A self-flagged submission escalates with no fabricated rule set."""
    from tests.wp32_helpers import claimed_task, submission_body

    task = claimed_task(project, 1)
    coder = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    records = install_event_recorder()

    submission = coder.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(requires_human_attention=True, risk_justification="risky migration"),
        format="json",
    )
    assert submission.status_code == 201, submission.content

    task.refresh_from_db()
    assert task.state == TaskState.IN_HUMAN_REVIEW
    # T8's Section 8.2 pair — whichever the submission's shape hit.
    assert task.review_reason in {ReviewReason.SELF_FLAGGED, ReviewReason.SCOPE_VIOLATION}

    entries = _entry_events(records)
    assert len(entries) == 1
    data = entries[0]["data"]
    assert set(data) == {"review_reason", "task_version"}, "no rule-details key at all"
    # T8's Section 8.2 pair — whichever the submission's shape hit.
    assert task.review_reason in {ReviewReason.SELF_FLAGGED, ReviewReason.SCOPE_VIOLATION}
    assert data["review_reason"] == task.review_reason
    assert data["review_reason"] in set(ReviewReason.values)


# --- the seam itself + minimization -------------------------------------------


def test_rule_details_hook_shapes_the_payload_and_clearing_restores_default(
    project: Project,
) -> None:
    """The MT-3.9-01 provider seam: override in, override out."""
    task = make_task(project, 3, state=TaskState.IN_PROGRESS, failure_retry_count=3)
    task.worker_agent_id = "sweeper-target"
    task.worker_session_id = "sess_sweeper"
    task.claimed_role = ClaimedRole.CODER
    task.lease_acquired_at = timezone.now()
    task.lease_expires_at = timezone.now()
    task.save()

    set_review_rule_details_hook(
        lambda _task, transition_id: {"policy_rule_results": [{"probe": transition_id}]}
    )
    records = install_event_recorder()
    dispatch_transition(
        task_id=task.pk, trigger="retry_exhausted", actor_type="system", actor_ref="sweeper"
    )
    assert _entry_events(records)[0]["data"]["policy_rule_results"] == [{"probe": "T9"}]

    set_review_rule_details_hook(None)  # back to the ambient default
    task.state = TaskState.IN_PROGRESS
    task.failure_retry_count = 3
    task.save()
    later = install_event_recorder()
    dispatch_transition(
        task_id=task.pk, trigger="retry_exhausted", actor_type="system", actor_ref="sweeper"
    )
    assert set(_entry_events(later)[0]["data"]) == {"review_reason", "task_version"}


@pytest.mark.parametrize("seed", [1, 2])
def test_payload_data_keys_stay_inside_the_closed_set(
    owner_client: JsonAPIClient, project: Project, policy_engine_installed: None, seed: int
) -> None:
    """No free-text evidence or unknown keys, engine or not (9.8/12.4)."""
    if seed == 1:
        task = auditable_with_patch(project, 5, patch=CRITICAL_PATCH)
        auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
        assert claim_as_auditor(auditor, task.pk).status_code == 200
        records = install_event_recorder()
        response = auditor.post(
            f"/api/v1/tasks/{task.pk}/audit-verdict",
            {
                "session_id": "sess_wp33_auditor",
                "lease_generation": 1,
                "task_id": task.pk,
                "verdict": "pass",
                "confidence": 4,
                "notes": "minimization probe",
                "evidence": {
                    "commands": [{"label": "tests", "command": "pytest -q", "exit_code": 0}]
                },
            },
            format="json",
        )
        assert response.status_code == 201, response.content
    else:
        task = auditable_task(project, 6)
        auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
        assert claim_as_auditor(auditor, task.pk).status_code == 200
        records = install_event_recorder()
        response = auditor.post(
            f"/api/v1/tasks/{task.pk}/audit-verdict",
            {
                "session_id": "sess_wp33_auditor",
                "lease_generation": 1,
                "task_id": task.pk,
                "verdict": "flag_risk",
                "confidence": 2,
                "notes": "minimization probe",
                "evidence": {
                    "commands": [{"label": "tests", "command": "pytest -q", "exit_code": 1}]
                },
            },
            format="json",
        )
        assert response.status_code == 201, response.content

    entries = _entry_events(records)
    assert len(entries) == 1
    assert set(entries[0]["data"]) <= DATA_KEYS, "closed key set (MT-3.9-01)"
    assert entries[0]["data"]["review_reason"] in set(ReviewReason.values)


def test_direct_dispatcher_call_without_a_reason_is_a_programming_error(
    project: Project,
) -> None:
    """An entry row that never set review_reason fails loudly, never silently."""
    task = make_task(project, 9, state=TaskState.IN_PROGRESS)
    task.worker_agent_id = "no-reason-worker"
    task.worker_session_id = "sess_no_reason"
    task.claimed_role = ClaimedRole.CODER
    task.lease_acquired_at = timezone.now()
    task.lease_expires_at = timezone.now()
    task.save()

    def _side_effect_without_reason(task: Task, context: Any) -> None:
        task.review_reason = ""  # wiring bug: no Section 8.4 member
        from apps.tasks.state_machine.guards import clear_coder_lease

        clear_coder_lease(task)  # the lease half is correct; only the reason is broken

    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T8",
            trigger="submit_flagged_buggy",
            from_states=frozenset({TaskState.IN_PROGRESS}),
            to_state=TaskState.IN_HUMAN_REVIEW,
            actor_types=frozenset({"agent"}),
            guard=None,
            side_effect=_side_effect_without_reason,
            event_type="task.transitioned",
            reason_code="submit_flagged",
            wired=True,
        ),
        replace=True,
    )
    with pytest.raises(ValueError, match="Section 8.4"):
        dispatch_transition(
            task_id=task.pk,
            trigger="submit_flagged_buggy",
            actor_type="agent",
            actor_ref="sess_buggy",
        )
    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS, "the whole dispatch rolled back"
    assert not Task.objects.filter(pk=task.pk, state=TaskState.IN_HUMAN_REVIEW).exists()
