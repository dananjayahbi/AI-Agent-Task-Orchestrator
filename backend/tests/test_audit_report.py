"""MT-3.3-04 — the Audit Report model, evidence round-trip and listing.

Run with ``pytest backend/tests -k audit_report -q``:

* **Field parity** — the model persists exactly the Section 7.2 Audit
  Report field set, nothing added or dropped (Section 20.5), with the
  two FK columns spelled ``task_id``/``resolution_id`` (7.2's names).
* **Confidence** — constrained to 1-5 at the model validators *and* the
  database check (a direct ORM write cannot smuggle 0 or 6 through).
* **Evidence** — round-trips the Section 10.5 structure (commands with
  label/command/exit_code, ``lint_clean``) without reshaping or
  dropping a single field (FR-AUD-02).
* **Policy fields** — ``policy_decision``/``policy_rule_results`` exist
  but stay ``null`` until the engine writes them (never faked here;
  the model permits exactly that later write for MT-3.4-06).
* **Listing** — ``GET /tasks/{id}/audit-reports``: caller Auditor/Owner
  with catalog-coded refusals, pagination.md's cursor envelope, and the
  documented order choice: **newest first** (reports accumulate per
  resolution across T12 audit retries).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditReport, VerdictChoice
from apps.projects.models import Project
from apps.tasks.models import Task, TaskResolution, TaskState

from .wp33_helpers import (
    active_policy_project,
    agent_client,
    auditable_task,
    claim_as_auditor,
    clean_throttle_cache,  # noqa: F401  (autouse)
    issue_agent_token,
    login_owner_client,
    make_task,
    restore_audit_registry,  # noqa: F401  (autouse)
    verdict_body,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (Section 9.2's owner-only rows)."""
    return login_owner_client()


# Section 7.2 "Audit Report" + Section 9.4's engine version, verbatim —
# the literal field-set assertion (the version column is MT-3.4-06's
# plan-mandated addition: §9.4 "the version is stored on each Audit
# Report"; MT-3.3-04 predates it).
PLAN_7_2_AUDIT_REPORT_FIELDS: tuple[str, ...] = (
    "id",
    "task",  # Section 7.2 spells it task_id (column + attname)
    "resolution",  # Section 7.2 spells it resolution_id (column + attname)
    "auditor_session_id",
    "evidence",
    "confidence",
    "auditor_notes",
    "proposed_verdict",
    "policy_decision",
    "policy_rule_results",
    "policy_engine_version",  # Section 9.4 traceability (MT-3.4-06)
    "created_at",
)

# The Section 10.5 evidence object the endpoint persists as supplied.
EVIDENCE_10_5: dict[str, Any] = {
    "commands": [
        {
            "label": "tests",
            "command": "pytest -q",
            "exit_code": 0,
            "summary": "12 passed",
        },
        {
            "label": "lint",
            "command": "ruff check .",
            "exit_code": 1,
        },
    ],
    "lint_clean": False,
    "changed_files": ["src/app.py", "tests/test_app.py"],
    "diff_stats": {"files": 2, "insertions": 40, "deletions": 3},
}


def _code(response: Any) -> str:
    """The catalog code of one standard envelope (five fields, asserted)."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


def _build(task: Task, resolution: TaskResolution, **overrides: Any) -> AuditReport:
    """An *unsaved* report row (for ``full_clean`` before any INSERT)."""
    payload: dict[str, Any] = {
        "task": task,
        "resolution": resolution,
        "auditor_session_id": "sess_wp33_reader",
        "evidence": {"commands": []},
        "confidence": 4,
        "proposed_verdict": VerdictChoice.PASS,
    }
    payload.update(overrides)
    return AuditReport(**payload)


def _report(task: Task, resolution: TaskResolution, **overrides: Any) -> AuditReport:
    """A stored report row directly (the listing's fixtures)."""
    report = _build(task, resolution, **overrides)
    report.save()
    return report


# --- model: field parity, constraints, engine-null fields --------------------


def test_model_field_set_matches_section_7_2_exactly() -> None:
    """Twelve fields: §7.2's eleven + §9.4's engine version (MT-3.4-06)."""
    names = tuple(field.name for field in AuditReport._meta.get_fields() if field.concrete)
    assert names == PLAN_7_2_AUDIT_REPORT_FIELDS, set(names) ^ set(PLAN_7_2_AUDIT_REPORT_FIELDS)

    task_field = AuditReport._meta.get_field("task")
    assert task_field.attname == "task_id", "the Section 7.2 FK column name"
    assert task_field.column == "task_id"
    resolution_field = AuditReport._meta.get_field("resolution")
    assert resolution_field.attname == "resolution_id", "the Section 7.2 FK column name"
    assert resolution_field.column == "resolution_id"
    assert AuditReport._meta.pk.name == "id", "the Section 7.2 identity field"


def test_confidence_is_constrained_to_1_to_5(project: Project) -> None:
    """Validators and the database check both refuse values outside 1-5."""
    task = auditable_task(project, 1)
    resolution = TaskResolution.objects.get(task=task)
    for bad in (0, 6):
        with pytest.raises(DjangoValidationError):
            _build(task, resolution, confidence=bad).full_clean()
        with pytest.raises(IntegrityError), transaction.atomic():
            _report(task, resolution, confidence=bad)
    for good in (1, 5):
        report = _report(task, resolution, confidence=good)
        report.full_clean()
        report.delete()  # the model allows the engine-era lifecycle writes


def test_proposed_verdict_is_the_section_10_5_enum(project: Project) -> None:
    """pass | flag_risk | fail in the database; nothing else writes."""
    task = auditable_task(project, 1)
    resolution = TaskResolution.objects.get(task=task)
    assert tuple(VerdictChoice.values) == ("pass", "flag_risk", "fail")
    with pytest.raises(IntegrityError), transaction.atomic():
        _report(task, resolution, proposed_verdict="maybe")


def test_policy_fields_stay_null_until_the_engine_writes_them(
    project: Project,
) -> None:
    """Nullable on creation; exactly the engine write is permitted."""
    from apps.audit.models import PolicyFieldsImmutable
    from apps.audit.policy.engine import EvaluationResult, RuleOutcome
    from apps.audit.policy.persist import persist_evaluation

    task = auditable_task(project, 1)
    resolution = TaskResolution.objects.get(task=task)
    report = _report(task, resolution)

    assert report.policy_decision is None, "never faked (Section 9.4; invariant 8.3.4)"
    assert report.policy_rule_results is None
    assert report.policy_engine_version is None

    # MT-3.4-06's guard: a direct write outside the engine path is
    # refused — the row is not insert-only, but its policy columns are.
    report.policy_decision = "escalate"
    report.policy_rule_results = [{"rule": "R1", "passed": False, "review_reason": "test_failure"}]
    with pytest.raises(PolicyFieldsImmutable):
        report.save()
    report.refresh_from_db()
    assert report.policy_decision is None

    # The engine's own persistence writes all three columns together.
    evaluation = EvaluationResult(
        decision="escalate",
        engine_version="1.0.0",
        rule_results=(
            RuleOutcome("R1", False, "test_failure"),
            *(RuleOutcome(f"R{i}", True, None) for i in range(2, 10)),
        ),
    )
    persist_evaluation(report, evaluation)
    report.refresh_from_db()
    assert report.policy_decision == "escalate"
    assert report.policy_engine_version == "1.0.0"
    assert report.policy_rule_results[0] == {
        "rule": "R1",
        "passed": False,
        "review_reason": "test_failure",
    }
    assert len(report.policy_rule_results) == 9


def test_report_accumulates_per_resolution_across_audit_retries(
    project: Project,
) -> None:
    """Recorded reading: T12 re-claims store a second row, first kept."""
    task = auditable_task(project, 1)
    resolution = TaskResolution.objects.get(task=task)
    first = _report(task, resolution, auditor_session_id="sess_wp33_aud_one")
    second = _report(task, resolution, auditor_session_id="sess_wp33_aud_two")

    rows = AuditReport.objects.filter(task=task)
    assert set(rows.values_list("id", flat=True)) == {first.pk, second.pk}


# --- persistence: the §10.5 evidence structure round-trips ------------------


def test_evidence_round_trips_the_10_5_shape(owner_client: APIClient, project: Project) -> None:
    """A verdict's evidence is stored verbatim — no reshaping, no drops."""
    task = auditable_task(project, 1)
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    assert claim_as_auditor(auditor, task.pk).status_code == 200

    response = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        verdict_body(
            task.pk,
            confidence=3,
            notes="honest audit",
            evidence=EVIDENCE_10_5,
        ),
    )

    assert response.status_code == 201, response.content
    report = AuditReport.objects.get(task=task)
    assert report.evidence == EVIDENCE_10_5, "commands, lint flag, files and stats as supplied"
    assert report.confidence == 3
    assert report.auditor_notes == "honest audit"
    assert report.proposed_verdict == "pass"
    assert report.auditor_session_id == "sess_wp33_auditor"
    assert report.resolution_id == TaskResolution.objects.get(task=task).pk
    # The response echoes the same §7.2 field set + §9.4's version.
    assert set(response.json()["report"]) == {
        "id",
        "task_id",
        "resolution_id",
        "auditor_session_id",
        "evidence",
        "confidence",
        "auditor_notes",
        "proposed_verdict",
        "policy_decision",
        "policy_rule_results",
        "policy_engine_version",
        "created_at",
    }


def test_acceptance_criteria_results_are_preserved_inside_evidence(
    owner_client: APIClient, project: Project
) -> None:
    """The §10.5 sibling input lands in the schemaless evidence JSON."""
    task = auditable_task(project, 1)
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    assert claim_as_auditor(auditor, task.pk).status_code == 200
    criteria = [{"criterion": "tests pass", "met": True}]

    response = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        verdict_body(task.pk, acceptance_criteria_results=criteria),
    )

    assert response.status_code == 201, response.content
    report = AuditReport.objects.get(task=task)
    assert report.evidence["acceptance_criteria_results"] == criteria
    assert report.evidence["commands"] == EVIDENCE_10_5["commands"][:0] + [
        {
            "label": "tests",
            "command": "pytest -q",
            "exit_code": 0,
            "summary": "all green",
        }
    ], "the evidence object itself is untouched"


# --- listing: callers, envelope, order, cursors ------------------------------


def test_listing_envelope_is_newest_first_and_paginated(
    owner_client: APIClient, project: Project
) -> None:
    """pagination.md envelope; order choice: newest first (documented)."""
    task = auditable_task(project, 1)
    resolution = TaskResolution.objects.get(task=task)
    older = _report(task, resolution, auditor_session_id="sess_wp33_older")
    newer = _report(task, resolution, auditor_session_id="sess_wp33_newer")
    # Deterministic timestamps regardless of the host clock's resolution.
    base = timezone.now() - timedelta(hours=1)
    AuditReport.objects.filter(pk=older.pk).update(created_at=base)
    AuditReport.objects.filter(pk=newer.pk).update(created_at=base + timedelta(minutes=5))

    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    page_one = client.get(f"/api/v1/tasks/{task.pk}/audit-reports", {"page_size": 1})

    assert page_one.status_code == 200, page_one.content
    body = page_one.json()
    assert set(body) == {"results", "next_cursor"}
    assert [row["id"] for row in body["results"]] == [str(newer.pk)]
    assert body["next_cursor"]

    page_two = client.get(
        f"/api/v1/tasks/{task.pk}/audit-reports",
        {"page_size": 1, "cursor": body["next_cursor"]},
    )
    assert page_two.status_code == 200, page_two.content
    assert [row["id"] for row in page_two.json()["results"]] == [str(older.pk)]
    assert page_two.json()["next_cursor"] is None

    # A mangled cursor is a client error from the closed catalog.
    broken = client.get(f"/api/v1/tasks/{task.pk}/audit-reports", {"cursor": "not-a-cursor"})
    assert broken.status_code == 400
    assert _code(broken) == "VALIDATION_ERROR"


def test_listing_callers_follow_the_audit_row(owner_client: APIClient, project: Project) -> None:
    """Auditor / Owner read; coder, device, anonymous refuse with catalog codes."""
    task = auditable_task(project, 1)
    resolution = TaskResolution.objects.get(task=task)
    _report(task, resolution)
    url = f"/api/v1/tasks/{task.pk}/audit-reports"

    anonymous = APIClient().get(url)
    assert anonymous.status_code == 401
    assert _code(anonymous) == "AUTH_REQUIRED"

    owner = owner_client.get(url)
    assert owner.status_code == 200, owner.content
    assert len(owner.json()["results"]) == 1

    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor")).get(url)
    assert auditor.status_code == 200

    coder = agent_client(issue_agent_token(owner_client, project.pk, "coder")).get(url)
    assert coder.status_code == 403
    assert _code(coder) == "ROLE_NOT_PERMITTED"

    device_registration = owner_client.post(
        "/api/v1/devices", {"platform": "android", "push_token": "apns-audit-reports"}
    )
    assert device_registration.status_code == 201, device_registration.content
    device = APIClient()
    device.credentials(HTTP_AUTHORIZATION=f"Bearer {device_registration.json()['token']}")
    device_response = device.get(url)
    assert device_response.status_code == 403
    assert _code(device_response) == "ROLE_NOT_PERMITTED"


def test_listing_scope_and_unknown_task_codes(owner_client: APIClient, project: Project) -> None:
    """ADR-004 zero-bleed first; unknown task answers TASK_NOT_FOUND."""
    task = auditable_task(project, 1)
    url = f"/api/v1/tasks/{task.pk}/audit-reports"

    other = active_policy_project(pid="PID00002")
    foreign = agent_client(issue_agent_token(owner_client, other.pk, "auditor")).get(url)
    assert foreign.status_code == 403
    assert _code(foreign) == "AUTH_FORBIDDEN_PROJECT"

    missing = owner_client.get("/api/v1/tasks/PID00001-T999/audit-reports")
    assert missing.status_code == 404
    assert _code(missing) == "TASK_NOT_FOUND"


def test_listing_of_a_task_without_reports_is_an_empty_page(
    owner_client: APIClient, project: Project
) -> None:
    """Empty tasks return an empty page, never a 404 or a crash."""
    task = make_task(project, 1, state=TaskState.DRAFT)
    response = owner_client.get(f"/api/v1/tasks/{task.pk}/audit-reports")
    assert response.status_code == 200
    assert response.json() == {"results": [], "next_cursor": None}
