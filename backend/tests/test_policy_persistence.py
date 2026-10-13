"""MT-3.4-06 — persist rule results and the engine version on every report.

Run with ``pytest backend/tests -k policy_persistence -q``:

* every evaluation persists **all nine** rules with per-rule pass/fail,
  the ``approve``/``escalate`` decision and the engine version
  (Section 9.4; §7.2 column semantics);
* the write is atomic with the transition (same dispatch transaction;
  a rollback takes the decision *and* its results);
* the engine is the only writer — direct instance saves, queryset
  updates, bulk updates and API bodies are all refused
  (``PolicyFieldsImmutable`` / strict serializer; invariant 8.3.4);
* ``GET /tasks/{id}/audit-reports`` returns the persisted results
  intact for the review panels (Section 13.2's rule table).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.db import IntegrityError, connection, transaction
from rest_framework.test import APIClient

from apps.audit.models import AuditReport, PolicyFieldsImmutable
from apps.audit.policy import ENGINE_VERSION, RULE_SLOTS
from apps.audit.policy.persist import persist_evaluation
from apps.audit.policy.wiring import ensure_policy_engine_wired
from apps.audit.serializers import AuditVerdictRequestSerializer
from apps.projects.models import Project
from apps.tasks.models import Task, TaskState

from .wp34_helpers import (  # noqa: F401  (autouse fixtures promoted)
    CRITICAL_PATCH,
    active_policy_project,
    agent_client,
    auditable_with_patch,
    claim_as_auditor,
    clean_throttle_cache,
    issue_agent_token,
    local_media,
    login_owner_client,
    restore_policy_registry,
    rule_result_rows,
    verdict_body,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def policy_engine_installed() -> None:
    """The real wiring under test (both seams; MT-3.4-07)."""
    ensure_policy_engine_wired()


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (the reports listing's Owner cell)."""
    return login_owner_client()


@pytest.fixture
def project() -> Project:
    """One active project with the default (all-pass shaped) policy."""
    return active_policy_project()


def _stored_report(task: Task, session_id: str = "sess_wp34_seed") -> AuditReport:
    """A fresh report row (the policy columns start ``null``)."""
    return AuditReport.objects.create(
        task=task,
        resolution=task.resolutions.get(),
        auditor_session_id=session_id,
        evidence={"commands": [{"label": "t", "command": "t", "exit_code": 0}]},
        confidence=4,
        proposed_verdict="pass",
    )


def _audited(
    owner_client: APIClient, project: Project, index: int = 1, **seed: Any
) -> tuple[Task, APIClient]:
    """A ``to_be_audited`` task on an independent auditor lease."""
    task = auditable_with_patch(project, index, **seed)
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    claimed = claim_as_auditor(auditor, task.pk)
    assert claimed.status_code == 200, claimed.content
    return task, auditor


# --- the engine-only write guard (invariant 8.3.4) --------------------------


def test_direct_orm_writes_to_policy_columns_are_refused(project: Project) -> None:
    """Instance save, queryset update and bulk_update all refuse."""
    task = auditable_with_patch(project, 1)
    report = _stored_report(task)

    report.policy_decision = "approve"
    with pytest.raises(PolicyFieldsImmutable):
        report.save()
    report.refresh_from_db()
    assert report.policy_decision is None

    with pytest.raises(PolicyFieldsImmutable):
        AuditReport.objects.filter(pk=report.pk).update(policy_decision="approve")
    with pytest.raises(PolicyFieldsImmutable):
        AuditReport.objects.filter(pk=report.pk).update(policy_engine_version="1.0.0")
    with pytest.raises(PolicyFieldsImmutable):
        AuditReport.objects.bulk_update([report], ["policy_rule_results"])
    # An update that does not touch the engine's columns still works.
    AuditReport.objects.filter(pk=report.pk).update(auditor_notes="panel note")


def test_api_bodies_cannot_carry_policy_columns() -> None:
    """The strict §10.5 input serializer refuses the engine's fields."""
    body: dict[str, Any] = {
        "session_id": "sess_wp34_api",
        "lease_generation": 1,
        "task_id": "PID00001-T001",
        "verdict": "pass",
        "confidence": 4,
        "notes": "",
        "evidence": {"commands": [{"label": "t", "command": "t", "exit_code": 0}]},
        "policy_decision": "approve",
        "policy_rule_results": [],
        "policy_engine_version": "9.9.9",
    }
    serializer = AuditVerdictRequestSerializer(data=body)
    with pytest.raises(Exception) as excinfo:  # DRF ValidationError
        serializer.is_valid(raise_exception=True)
    assert "policy_decision" in str(excinfo.value)


def test_database_pairs_decision_with_results_and_version(project: Project) -> None:
    """Check constraints: no decision without results/version, ever."""
    task = auditable_with_patch(project, 1)
    report = _stored_report(task, session_id="sess_wp34_pairing")
    # ORM doors are closed; the database itself still enforces the pairing.
    with pytest.raises(IntegrityError), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE audit_auditreport SET policy_decision = 'escalate' WHERE id = %s",
                # SQLite stores UUIDField as 32-char hex without dashes.
                [report.pk.hex],
            )


# --- persistence through the engine path -----------------------------------


def test_engine_write_lands_all_nine_results_and_version(
    owner_client: APIClient, project: Project, policy_engine_installed: None
) -> None:
    """A clean audited verdict persists approve + nine passes + version."""
    task, auditor = _audited(owner_client, project)

    response = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        verdict_body(task.pk, confidence=4),
    )
    assert response.status_code == 201, response.content

    report = AuditReport.objects.get(task=task)
    assert report.policy_decision == "approve"
    assert report.policy_engine_version == ENGINE_VERSION
    results = report.policy_rule_results
    assert isinstance(results, list) and len(results) == len(RULE_SLOTS)
    assert [row["rule"] for row in results] == list(RULE_SLOTS)
    assert all(row["passed"] is True for row in results)
    assert all(row["review_reason"] is None for row in results)


def test_escalation_persists_every_failing_reason(
    owner_client: APIClient, project: Project, policy_engine_installed: None
) -> None:
    """Multiple failures persist per-rule reasons; primary is R1→R9 first."""
    task, auditor = _audited(
        owner_client,
        project,
        patch=CRITICAL_PATCH,
        target_scope=(".github/**", "src/**"),  # in scope for R2; R3 still fires
    )

    response = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        # R1 fails too: a non-zero exit code in the evidence.
        verdict_body(
            task.pk,
            evidence={"commands": [{"label": "tests", "command": "pytest -q", "exit_code": 1}]},
        ),
    )
    assert response.status_code == 201, response.content
    assert response.json()["task"]["review_reason"] == "test_failure", "primary: R1 first"

    report = AuditReport.objects.get(task=task)
    assert report.policy_decision == "escalate"
    assert report.policy_engine_version == ENGINE_VERSION
    rows = rule_result_rows(report.policy_rule_results)
    failed = {row["rule"]: row["review_reason"] for row in rows if not row["passed"]}
    assert failed == {"R1": "test_failure", "R3": "critical_path_changed"}


def test_persist_none_writes_nothing_fail_closed(project: Project) -> None:
    """The seam default (no engine) persists nothing — never faked."""
    task = auditable_with_patch(project, 1)
    report = _stored_report(task, session_id="sess_wp34_none")

    persist_evaluation(report, None)
    report.refresh_from_db()
    assert report.policy_decision is None
    assert report.policy_rule_results is None
    assert report.policy_engine_version is None


def test_rollback_takes_the_decision_with_its_results(
    owner_client: APIClient, project: Project, policy_engine_installed: None
) -> None:
    """Atomicity: a failed dispatch leaves neither decision nor results."""
    from apps.audit.decision import resolve_audit_decision
    from apps.audit.policy.wiring import audit_decision_hook

    task, _auditor = _audited(owner_client, project)
    resolution = task.resolutions.get()
    report = _stored_report(task)

    decision = audit_decision_hook(task, resolution, report)
    assert decision.approve is True and decision.evaluation is not None
    with pytest.raises(RuntimeError), transaction.atomic():
        persist_evaluation(report, decision.evaluation)
        raise RuntimeError("simulated dispatch failure")
    report.refresh_from_db()
    assert report.policy_decision is None, "decision + results + version rolled back together"
    assert report.policy_rule_results is None
    assert report.policy_engine_version is None
    # The same seam consult is what the service and the rows agree on.
    assert resolve_audit_decision(task, resolution, report).approve is True


def test_listing_round_trips_persisted_results_for_the_panel(
    owner_client: APIClient, project: Project, policy_engine_installed: None
) -> None:
    """GET /tasks/{id}/audit-reports returns results + version intact."""
    task, auditor = _audited(owner_client, project)
    posted = auditor.post(f"/api/v1/tasks/{task.pk}/audit-verdict", verdict_body(task.pk))
    assert posted.status_code == 201, posted.content

    listing = owner_client.get(f"/api/v1/tasks/{task.pk}/audit-reports")
    assert listing.status_code == 200, listing.content
    results = listing.json()["results"]
    assert len(results) == 1
    stored = results[0]
    assert stored["policy_decision"] == "approve"
    assert stored["policy_engine_version"] == ENGINE_VERSION
    assert [row["rule"] for row in stored["policy_rule_results"]] == list(RULE_SLOTS)
    # The 201 body carries the same persisted state (same row instance).
    assert posted.json()["report"]["policy_rule_results"] == stored["policy_rule_results"]


def test_each_verdict_row_keeps_its_own_engine_write(
    owner_client: APIClient, project: Project, policy_engine_installed: None
) -> None:
    """Lifecycle: T13 leaves the report's write intact; retries can't add."""
    task, auditor = _audited(owner_client, project)
    first = auditor.post(f"/api/v1/tasks/{task.pk}/audit-verdict", verdict_body(task.pk))
    assert first.status_code == 201, first.content
    assert first.json()["trigger"] == "audit_verdict_pass"

    task.refresh_from_db()
    assert task.state == TaskState.TO_BE_AUDITED, "merge-pending stays in-column (8.1)"
    assert task.merge_status == "pending"

    # The audit lease concluded with T13, so a replay dies at the fencing
    # gate — no second report, no second write (Section 9.2 idempotency).
    second = auditor.post(f"/api/v1/tasks/{task.pk}/audit-verdict", verdict_body(task.pk))
    assert second.status_code == 409
    row = AuditReport.objects.get(task=task)
    assert row.policy_decision == "approve"
    assert len(rule_result_rows(row.policy_rule_results)) == len(RULE_SLOTS)
    assert row.policy_engine_version == ENGINE_VERSION
