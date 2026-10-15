"""MT-3.9-03 — escalation reason-coverage: one table row per Section 8.4 reason.

The anti-rot suite WP-3.9's acceptance names ("each review reason yields
one event with rule details"): a **table-driven** pass (Section 18's
unit-row discipline) where every canonical review reason is produced by
the transition that actually owns it — never a synthetic hook call —
and every row asserts the same ``review.requested`` contract:

* exactly **one** entry event per entry transition (never zero, never
  two — the push seam stays a single downstream consumer);
* the Section 9.6 envelope verbatim (``type`` catalog membership,
  ``project_id``, ``task_id``, ``occurred_at``, ``actor``) plus the
  dedupe key's ``task_version``;
* the canonical Section 8.4 ``review_reason`` on the task **and** in
  the event data;
* T14 rows carry the Policy Engine's persisted rule details keyed on
  the **failed rule id** (never message text — wording evolves, the
  rule outcome is the contract); T8/T9/T18 rows carry no
  ``policy_rule_results`` key at all (absence is expressible, never a
  fabricated rule set — MT-3.9-02).

Transitions under test (Section 8.2's entering rows):

* **T8** — ``self_flagged`` (self-flagged submit) and ``scope_violation``
  (changed files outside ``target_scope``), through the real submission
  endpoint;
* **T9** — ``retry_exhausted`` at the ``failure_retry_count`` ceiling,
  through the sweeper's dispatch;
* **T14** — every Section 9.4 rule R1–R9 failing alone through the real
  verdict endpoint with the engine installed (each rule's representative
  failure — rule *correctness* is WP-3.4's own suite);
* **T18** — ``merge_conflict``, now that WP-3.7 wires the merge rows
  (the reason MT-3.9-03 was deferred on; the executor's row drives the
  same generic entry hook).

The **coverage guard** is the device that keeps this honest: the suite
fails if Section 8.4's enum holds a reason no row exercises, so a future
enum addition forces a test here rather than shipping untested.

Run with ``pytest backend/tests -k escalation_reasons -q``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from django.utils import timezone

from apps.audit.policy.wiring import ensure_policy_engine_wired
from apps.events.catalog import EVENT_TYPES
from apps.merge.transitions import ensure_merge_wired
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import (
    ClaimedRole,
    MergeStatus,
    ReviewReason,
    Task,
    TaskState,
)
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.hooks import set_review_rule_details_hook
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY
from tests.wp15_helpers import install_event_recorder, make_project, make_task, reset_hooks
from tests.wp16_helpers import (  # noqa: F401  (autouse: registry restore)
    claim,
    make_pending_task,
    restore_lease_registry,
)
from tests.wp32_helpers import (  # noqa: F401  (autouse: registry restore)
    SAMPLE_PATCH,
    SAMPLE_SHA,
    claimed_task,
    restore_submission_registry,
    submission_body,
)
from tests.wp33_helpers import (  # noqa: F401  (restore_audit_registry is NOT wanted here:
    # wp34's restore_policy_registry covers the seam pinning this suite needs)
    JsonAPIClient,
    agent_client,
    claim_as_auditor,
    issue_agent_token,
    login_owner_client,
)
from tests.wp34_helpers import (  # noqa: F401  (autouse fixtures promoted)
    CLEAN_PATCH,
    CRITICAL_PATCH,
    MIGRATION_PATCH,
    OUT_OF_SCOPE_PATCH,
    SENSITIVE_GLOB_PATCH,
    auditable_with_patch,
    clean_throttle_cache,
    local_media,
    restore_policy_registry,
    verdict_body,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def review_registry() -> Iterator[None]:
    """Snapshot the registry; run against the ambient engine; restore after.

    The wp32/wp34 fixtures pin the *decision* seams fail-closed around
    every test; this one additionally clears any rule-details override
    so T14 rows answer from the audit app's production reader only.
    """
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
    return make_project(name="WP-3.9 reason coverage")


# --- the table ------------------------------------------------------------


@dataclass(frozen=True)
class ReasonRow:
    """One canonical reason, driven by the transition that produces it."""

    case_id: str
    reason: str
    transition_id: str
    #: T14 rows: the Section 9.4 rule that must fail (key of the contract);
    #: ``None`` for T8/T9/T18 rows, which carry no rule details at all.
    expects_rule: str | None
    drive: Callable[[Project, JsonAPIClient], tuple[list[Any], Task, dict[str, str]]]


def _records_and(
    task: Task, actor: dict[str, str], records: list[Any]
) -> tuple[list[Any], Task, dict[str, str]]:
    """Bundle a driver's return triple."""
    return records, task, actor


# --- T8 drivers (real submission endpoint) ---------------------------------


def _drive_t8_self_flagged(project: Project, owner_client: JsonAPIClient) -> Any:
    """A self-flagged, in-scope submission takes T8 with ``self_flagged``."""
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])
    coder = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    records = install_event_recorder()
    response = coder.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(requires_human_attention=True, risk_justification="flagged by coder"),
        format="json",
    )
    assert response.status_code == 201, response.content
    return _records_and(task, {"type": "agent", "ref": "sess_wp32"}, records)


def _drive_t8_scope_violation(project: Project, owner_client: JsonAPIClient) -> Any:
    """An out-of-scope submission takes T8 with ``scope_violation``."""
    task = claimed_task(project, 1, target_scope=["src/**"])  # SAMPLE_PATCH hits docs/
    coder = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    records = install_event_recorder()
    response = coder.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(requires_human_attention=False),
        format="json",
    )
    assert response.status_code == 201, response.content
    return _records_and(task, {"type": "agent", "ref": "sess_wp32"}, records)


# --- T9 driver (the sweeper's dispatch) -------------------------------------


def _drive_t9(project: Project, owner_client: JsonAPIClient) -> Any:
    """A task at the retry ceiling enters with ``retry_exhausted``."""
    task = make_task(project, 1, state=TaskState.IN_PROGRESS, failure_retry_count=3)
    task.worker_agent_id = "claude-code-session-98b2"
    task.worker_session_id = "sess_7f3c91d0a2b44e"
    task.claimed_role = ClaimedRole.CODER
    task.lease_acquired_at = timezone.now()
    task.lease_expires_at = timezone.now()
    task.save()
    records = install_event_recorder()
    dispatch_transition(
        task_id=task.pk, trigger="retry_exhausted", actor_type="system", actor_ref="sweeper"
    )
    return _records_and(task, {"type": "system", "ref": "sweeper"}, records)


# --- T14 driver factory (one representative failure per Section 9.4 rule) --


def _t14_driver(
    rule: str,
    verdict_overrides: dict[str, Any],
    seed_overrides: dict[str, Any],
    *,
    disable_auto_complete: bool = False,
) -> Callable[[Project, JsonAPIClient], Any]:
    """Build the T14 driver for one rule failing alone (Section 9.4)."""

    def drive(project: Project, owner_client: JsonAPIClient) -> Any:
        ensure_policy_engine_wired()
        if disable_auto_complete:
            # R9's sole input: the Section 7.2 switch, flipped alone.
            ProjectPolicy.objects.update(auto_complete_enabled=False)
        task = auditable_with_patch(project, 1, **seed_overrides)
        auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
        assert claim_as_auditor(auditor, task.pk).status_code == 200
        records = install_event_recorder()
        response = auditor.post(
            f"/api/v1/tasks/{task.pk}/audit-verdict",
            verdict_body(task.pk, **verdict_overrides),
        )
        assert response.status_code == 201, response.content
        return _records_and(task, {"type": "agent", "ref": "sess_wp33_auditor"}, records)

    drive.__name__ = f"drive_t14_{rule.lower()}"
    return drive


# --- T18 driver (WP-3.7's wired merge row) ---------------------------------


def _drive_t18(project: Project, owner_client: JsonAPIClient) -> Any:
    """The executor's reported conflict enters with ``merge_conflict``."""
    ensure_merge_wired()
    task = make_task(
        project,
        1,
        state=TaskState.TO_BE_AUDITED,
        merge_status=MergeStatus.PENDING,
        attempt_number=1,
    )
    records = install_event_recorder()
    dispatch_transition(
        task_id=task.pk,
        trigger="merge_failed",
        actor_type="agent",
        actor_ref="merge-executor",
        extra={"merge_status": MergeStatus.CONFLICT},
    )
    return _records_and(task, {"type": "agent", "ref": "merge-executor"}, records)


#: One row per canonical reason (Section 8.4's twelve verbatim);
#: ``scope_violation`` appears on both entering rows that produce it
#: (T8's service verdict and T14's R2), per the MT's coverage table.
REASON_TABLE: tuple[ReasonRow, ...] = (
    ReasonRow("T8-self_flagged", ReviewReason.SELF_FLAGGED, "T8", None, _drive_t8_self_flagged),
    ReasonRow(
        "T8-scope_violation", ReviewReason.SCOPE_VIOLATION, "T8", None, _drive_t8_scope_violation
    ),
    ReasonRow("T9-retry_exhausted", ReviewReason.RETRY_EXHAUSTED, "T9", None, _drive_t9),
    ReasonRow(
        "T14-R1-test_failure",
        ReviewReason.TEST_FAILURE,
        "T14",
        "R1",
        _t14_driver(
            "R1",
            {"evidence": {"commands": [{"label": "t", "command": "pytest", "exit_code": 1}]}},
            {},
        ),
    ),
    ReasonRow(
        "T14-R2-scope_violation",
        ReviewReason.SCOPE_VIOLATION,
        "T14",
        "R2",
        _t14_driver("R2", {}, {"patch": OUT_OF_SCOPE_PATCH, "target_scope": ("src/**",)}),
    ),
    ReasonRow(
        "T14-R3-critical_path_changed",
        ReviewReason.CRITICAL_PATH_CHANGED,
        "T14",
        "R3",
        _t14_driver("R3", {}, {"patch": CRITICAL_PATCH, "target_scope": (".github/**", "src/**")}),
    ),
    ReasonRow(
        "T14-R4-migration_detected",
        ReviewReason.MIGRATION_DETECTED,
        "T14",
        "R4",
        _t14_driver("R4", {}, {"patch": MIGRATION_PATCH, "target_scope": ("alembic/**", "src/**")}),
    ),
    ReasonRow(
        "T14-R5-sensitive_config_changed",
        ReviewReason.SENSITIVE_CONFIG_CHANGED,
        "T14",
        "R5",
        _t14_driver("R5", {}, {"patch": SENSITIVE_GLOB_PATCH, "target_scope": (".env*", "src/**")}),
    ),
    ReasonRow(
        "T14-R6-diff_over_threshold",
        ReviewReason.DIFF_OVER_THRESHOLD,
        "T14",
        "R6",
        _t14_driver(
            "R6",
            {},
            {"patch": CLEAN_PATCH, "diff_summary": {"files": 1, "insertions": 251, "deletions": 0}},
        ),
    ),
    ReasonRow(
        "T14-R7-low_confidence",
        ReviewReason.LOW_CONFIDENCE,
        "T14",
        "R7",
        _t14_driver("R7", {"confidence": 3}, {}),
    ),
    ReasonRow(
        "T14-R8-auditor_flagged",
        ReviewReason.AUDITOR_FLAGGED,
        "T14",
        "R8",
        _t14_driver("R8", {"verdict": "flag_risk"}, {}),
    ),
    ReasonRow(
        "T14-R9-policy_forced_review",
        ReviewReason.POLICY_FORCED_REVIEW,
        "T14",
        "R9",
        _t14_driver("R9", {}, {}, disable_auto_complete=True),
    ),
    ReasonRow("T18-merge_conflict", ReviewReason.MERGE_CONFLICT, "T18", None, _drive_t18),
)


# --- the contract, asserted once per row ------------------------------------


@pytest.mark.parametrize("row", REASON_TABLE, ids=[row.case_id for row in REASON_TABLE])
def test_each_reason_yields_exactly_one_review_requested(
    row: ReasonRow, project: Project, owner_client: JsonAPIClient
) -> None:
    """One entry event, the canonical reason, the Section 9.6 envelope."""
    records, task, actor = row.drive(project, owner_client)

    entries = [dict(record) for record in records if record["type"] == "review.requested"]
    assert len(entries) == 1, f"{row.case_id}: exactly one review.requested per entry"
    entry = entries[0]

    # Envelope, Section 9.6 verbatim.
    assert entry["type"] == "review.requested"
    assert entry["type"] in EVENT_TYPES, "catalog membership (20.4 item 6)"
    assert entry["project_id"] == project.pk
    assert entry["task_id"] == task.pk
    assert entry["occurred_at"] is not None
    assert entry["actor"] == actor

    # The canonical reason on the task and in the event data.
    data = entry["data"]
    assert data["review_reason"] == row.reason
    assert data["review_reason"] in set(ReviewReason.values), "Section 8.4 enum only"
    task.refresh_from_db()
    assert task.review_reason == row.reason
    assert data["task_version"] == task.version, "Section 9.8 dedupe key half"

    if row.expects_rule is not None:
        # T14: the persisted rule details, keyed on the failed rule id.
        results = data["policy_rule_results"]
        failed = [outcome for outcome in results if not outcome["passed"]]
        assert [outcome["rule"] for outcome in failed] == [row.expects_rule], (
            f"{row.case_id}: exactly {row.expects_rule} failed in {results}"
        )
        assert failed[0]["review_reason"] == row.reason
    else:
        # T8/T9/T18: reason + version only — no fabricated rule set.
        assert "policy_rule_results" not in data
        assert set(data) == {"review_reason", "task_version"}


def test_the_table_covers_every_section_8_4_reason() -> None:
    """The coverage guard: an enum reason without a row fails here.

    Section 8.4's canonical twelve are written out independently below
    (plan first — Section 20.5 traceability): a future enum addition
    breaks this equality until this table grows a row for it.
    """
    canonical_twelve = {
        "self_flagged",
        "scope_violation",
        "test_failure",
        "migration_detected",
        "sensitive_config_changed",
        "critical_path_changed",
        "diff_over_threshold",
        "low_confidence",
        "retry_exhausted",
        "merge_conflict",
        "auditor_flagged",
        "policy_forced_review",
    }
    covered = {row.reason for row in REASON_TABLE}
    assert covered == set(ReviewReason.values), "the model enum is Section 8.4 verbatim"
    assert covered == canonical_twelve, "the table exercises every canonical reason"


# --- negative controls ------------------------------------------------------


def test_non_entry_transitions_emit_no_review_requested(
    project: Project, owner_client: JsonAPIClient
) -> None:
    """T4 (claim), T7 (clean submit) and T17 (merge completion) stay quiet."""
    records = install_event_recorder()

    # T4: a claim lands in_progress — no entry, no event. The lease is
    # then released (T6) so the project's ``max_concurrent_tasks`` slot
    # is free for the submission seed below.
    from apps.leases.release import release_task

    claimed = make_pending_task(project, 1)
    claim(claimed, session_id="sess_ctrl_claim")
    release_task(
        task_id=claimed.pk,
        session_id="sess_ctrl_claim",
        lease_generation=1,
        actor_type="agent",
        actor_ref="sess_ctrl_claim",
    )

    # T7: a clean in-scope submission reaches to_be_audited — not a review entry.
    submitted = claimed_task(project, 2, target_scope=["src/**", "docs/**"])
    coder = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    response = coder.post(
        f"/api/v1/tasks/{submitted.pk}/resolution", submission_body(), format="json"
    )
    assert response.status_code == 201, response.content
    submitted.refresh_from_db()
    assert submitted.state == TaskState.TO_BE_AUDITED

    # T17: a reported merge completes the carrier — the far side of entry.
    ensure_merge_wired()
    carrier = make_task(
        project,
        3,
        state=TaskState.TO_BE_AUDITED,
        merge_status=MergeStatus.PENDING,
        attempt_number=1,
    )
    dispatch_transition(
        task_id=carrier.pk,
        trigger="merge_succeeded",
        actor_type="agent",
        actor_ref="merge-executor",
        extra={"merge_sha": "aaaabbbbccccddddeeeeffff0000111122223333"},  # pragma: allowlist secret
    )
    carrier.refresh_from_db()
    assert carrier.state == TaskState.COMPLETED

    assert [record["type"] for record in records if record["type"] == "review.requested"] == []
    # The three transitions themselves did fire — the recorder saw each
    # row's own catalog event (T4 ``task.claimed``, T7
    # ``task.transitioned`` → to_be_audited, T17 ``merge.succeeded``).
    assert any(record["type"] == "task.claimed" for record in records)
    t7 = [record for record in records if record["type"] == "task.transitioned"]
    assert [record["data"]["to_state"] for record in t7] == [TaskState.TO_BE_AUDITED]
    merged = [record for record in records if record["type"] == "merge.succeeded"]
    assert len(merged) == 1 and merged[0]["task_id"] == carrier.pk


def test_table_carries_no_invented_transition_or_reason() -> None:
    """Rows name only Section 8.2 transitions and Section 8.4 reasons."""
    assert {row.transition_id for row in REASON_TABLE} <= {"T8", "T9", "T14", "T18"}
    for row in REASON_TABLE:
        assert row.reason in set(ReviewReason.values), row.case_id
