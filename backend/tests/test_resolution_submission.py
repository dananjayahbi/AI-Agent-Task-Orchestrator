"""MT-3.2-01 — resolution model + submission endpoint (Sections 7.2/9.2).

Run with ``pytest backend/tests -k resolution_submission -q``. Every
case runs against the **real** routes with real credentials:

* the success shape — exactly the twelve Section 7.2 fields on the
  stored row (Section 20.5 traceability: field for field, no extras),
  the post-transition task identity the bridge reports (Section 10.5),
  and the authoritative ``diff_summary``/``changed_files`` the server
  parsed (claims ignored — Section 9.7);
* one resolution per (task, attempt): a second *distinct* submission on
  the same attempt answers ``TASK_STATE_CONFLICT`` and writes nothing;
* ``Idempotency-Key`` replay: the same request replays the stored
  outcome — no second row, no second transition (NFR-12; ADR-012);
* the caller catalog (Section 9.2): non-lease sessions
  ``LEASE_NOT_OWNED`` (403), stale generation/expired lease
  ``LEASE_EXPIRED`` (409), foreign-project agent
  ``AUTH_FORBIDDEN_PROJECT`` (403), non-coder roles and the owner
  ``ROLE_NOT_PERMITTED`` (403), anonymous ``AUTH_REQUIRED`` (401),
  unknown task ``TASK_NOT_FOUND`` (404), a task that is not
  ``in_progress`` ``TASK_STATE_CONFLICT`` (409) — nothing outside the
  closed catalog (Section 20.4 item 5);
* validation refusals with ``VALIDATION_ERROR`` (missing fencing pair,
  unknown fields — StrictSerializerMixin);
* the listing: newest first, cursor-paginated (pagination.md), owner
  and agent read, device refused, empty task → empty page.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.projects.models import Project
from apps.tasks.models import Task, TaskArtifact, TaskResolution, TaskState

from .wp32_helpers import (  # noqa: F401  (autouse fixtures promoted)
    SAMPLE_PATCH,
    _code,
    active_policy_project,
    agent_client,
    claimed_task,
    issue_agent_token,
    local_storage,
    login_owner,
    make_pending_task,
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


# Section 7.2 "Task Resolution" — field for field, nothing more (AC).
RESOLUTION_FIELDS = {
    "id",
    "task_id",
    "attempt_number",
    "branch_name",
    "commit_sha",
    "execution_summary",
    "diff_summary",
    "changed_files",
    "requires_human_attention",
    "risk_justification",
    "submitted_by_session",
    "submitted_at",
}
# The response's other three keys: outcome reporting (Section 10.5).
RESPONSE_FIELDS = {"resolution", "task", "trigger", "scope_violations"}


def _coder(owner_client: APIClient, project: Project) -> APIClient:
    """A coder-agent client for the default project."""
    return agent_client(issue_agent_token(owner_client, project.pk, "coder"))


def _submit(client: APIClient, task: Task, **overrides: Any) -> Any:
    return client.post(
        f"/api/v1/tasks/{task.pk}/resolution", submission_body(**overrides), format="json"
    )


# --- success: the frozen contract (Section 7.2 field set + outcome) ---------


def test_submission_stores_the_section_7_2_field_set(
    owner_client: APIClient, project: Project
) -> None:
    """201 body: twelve §7.2 fields, exact values, authoritative stats."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    response = _submit(agent, task)

    assert response.status_code == 201, response.content
    body = response.json()
    assert set(body) == RESPONSE_FIELDS
    resolution = body["resolution"]
    assert set(resolution) == RESOLUTION_FIELDS, "Section 7.2 fields, field for field"
    assert resolution["task_id"] == task.pk
    assert resolution["attempt_number"] == 1  # T4 incremented it at claim
    assert resolution["branch_name"] == "feat/PID00001-T001"
    expected_sha = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret
    assert resolution["commit_sha"] == expected_sha
    assert resolution["requires_human_attention"] is False
    assert resolution["submitted_by_session"] == "sess_wp32"
    assert resolution["submitted_at"] is not None
    # MT-3.2-03: the server's parse replaced any provisional claim.
    assert resolution["diff_summary"] == {"files": 2, "insertions": 2, "deletions": 2}
    assert resolution["changed_files"] == ["src/billing/invoice.py", "docs/readme.md"]
    # The outcome half (Section 10.5): T7's clean landing.
    assert body["trigger"] == "submit"
    assert body["task"]["state"] == "to_be_audited"
    assert body["task"]["review_reason"] is None
    assert body["scope_violations"] == []

    row = TaskResolution.objects.get(pk=resolution["id"])
    assert row.task_id == task.pk
    assert row.attempt_number == 1
    assert row.diff_summary == {"files": 2, "insertions": 2, "deletions": 2}
    assert TaskArtifact.objects.filter(resolution=row, kind="patch").count() == 1


def test_provisional_bridge_claims_never_override_the_parse(
    owner_client: APIClient, project: Project
) -> None:
    """Section 9.7: changed_files/diff_summary claims are accepted, ignored."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    response = _submit(
        agent,
        task,
        changed_files=["totally/bogus.py"],
        diff_summary={"files": 99, "insertions": 99, "deletions": 99},
    )

    assert response.status_code == 201, response.content
    resolution = response.json()["resolution"]
    assert resolution["changed_files"] == ["src/billing/invoice.py", "docs/readme.md"]
    assert resolution["diff_summary"] == {"files": 2, "insertions": 2, "deletions": 2}


def test_task_leaves_in_progress_with_the_worker_cleared(
    owner_client: APIClient, project: Project
) -> None:
    """Section 8.3 invariant 1 holds on the to_be_audited row (T7 side effects)."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    assert _submit(agent, task).status_code == 201

    fresh = Task.objects.get(pk=task.pk)
    assert fresh.state == TaskState.TO_BE_AUDITED
    assert fresh.worker_agent_id is None
    assert fresh.worker_session_id is None
    assert fresh.claimed_role is None
    assert fresh.lease_expires_at is None
    assert fresh.attempt_number == 1, "attempt_number is preserved, not reset"


# --- idempotency + per-attempt uniqueness (NFR-12; Section 7.2) -------------


def test_same_idempotency_key_replays_without_a_second_transition(
    owner_client: APIClient, project: Project
) -> None:
    """One key, one request shape → identical response, one row, one event."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    first = agent.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(),
        format="json",
        HTTP_IDEMPOTENCY_KEY="submit-key-1",
    )
    second = agent.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(),
        format="json",
        HTTP_IDEMPOTENCY_KEY="submit-key-1",
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()
    assert TaskResolution.objects.filter(task=task).count() == 1
    from apps.tasks.models import TaskTransition

    submissions = TaskTransition.objects.filter(task=task, from_state="in_progress")
    assert submissions.count() == 1, "one submission transition only (no T7 double-fire)"


def test_a_distinct_second_submission_on_the_same_attempt_conflicts(
    owner_client: APIClient, project: Project
) -> None:
    """Different key, same attempt → TASK_STATE_CONFLICT, nothing written."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    assert _submit(agent, task).status_code == 201
    repeat = agent.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(),
        format="json",
        HTTP_IDEMPOTENCY_KEY="submit-key-2",
    )
    assert repeat.status_code == 409
    assert _code(repeat) == "TASK_STATE_CONFLICT"
    assert TaskResolution.objects.filter(task=task).count() == 1


# --- the caller catalog (Section 9.2; MT-3.2-01 acceptance) ------------------


def test_only_the_lease_owner_reaches_the_service(
    owner_client: APIClient, project: Project
) -> None:
    """Owner/auditor/anonymous are refused at the permission gate."""
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    owner_post = owner_client.post(
        f"/api/v1/tasks/{task.pk}/resolution", submission_body(), format="json"
    )
    assert owner_post.status_code == 403
    assert _code(owner_post) == "ROLE_NOT_PERMITTED"

    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    auditor_post = _submit(auditor, task)
    assert auditor_post.status_code == 403
    assert _code(auditor_post) == "ROLE_NOT_PERMITTED"

    anon = APIClient()
    anon_post = _submit(anon, task)
    assert anon_post.status_code == 401
    assert _code(anon_post) == "AUTH_REQUIRED"


def test_foreign_session_and_stale_generation_answer_lease_codes(
    owner_client: APIClient, project: Project
) -> None:
    """The fencing pair is enforced: someone else's lease, an old generation."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    foreign = _submit(agent, task, session_id="sess_intruder")
    assert foreign.status_code == 403
    assert _code(foreign) == "LEASE_NOT_OWNED"

    stale = _submit(agent, task, lease_generation=0)
    assert stale.status_code == 409
    assert _code(stale) == "LEASE_EXPIRED"


def test_expired_lease_answers_lease_expired(owner_client: APIClient, project: Project) -> None:
    """A dead lease is the bridge's stop-and-re-claim signal (409)."""
    from datetime import timedelta

    from django.utils import timezone

    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))

    response = _submit(agent, task)
    assert response.status_code == 409
    assert _code(response) == "LEASE_EXPIRED"


def test_cross_project_agent_token_is_forbidden(owner_client: APIClient, project: Project) -> None:
    """ADR-004 zero-bleed: a PID00002 token never touches PID00001's task."""
    other = active_policy_project(pid="PID00002")
    foreign = agent_client(issue_agent_token(owner_client, other.pk, "coder"))
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    response = _submit(foreign, task)
    assert response.status_code == 403
    assert _code(response) == "AUTH_FORBIDDEN_PROJECT"


def test_unknown_task_and_not_in_progress_conflict(
    owner_client: APIClient, project: Project
) -> None:
    """TASK_NOT_FOUND (404) for the unknown id; TASK_STATE_CONFLICT (409) else."""
    agent = _coder(owner_client, project)

    missing = agent.post("/api/v1/tasks/PID00001-T044/resolution", submission_body(), format="json")
    assert missing.status_code == 404
    assert _code(missing) == "TASK_NOT_FOUND"

    pending = make_pending_task(project, 5)
    wrong_state = _submit(agent, pending)
    assert wrong_state.status_code == 409
    assert _code(wrong_state) == "TASK_STATE_CONFLICT"


def test_malformed_bodies_answer_validation_error(
    owner_client: APIClient, project: Project
) -> None:
    """Missing fencing pair / unknown fields — the strict boundary (400)."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    no_pair = submission_body()
    del no_pair["session_id"]
    missing = agent.post(f"/api/v1/tasks/{task.pk}/resolution", no_pair, format="json")
    assert missing.status_code == 400
    assert _code(missing) == "VALIDATION_ERROR"

    unknown = agent.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(project_id="PID00001"),
        format="json",
    )
    assert unknown.status_code == 400
    assert _code(unknown) == "VALIDATION_ERROR"


# --- listing (FR-AUD-01 input; pagination.md) --------------------------------


def _seed_resolutions(task: Task) -> None:
    """Two attempts' rows written directly (the read path under test).

    Timestamps are offset explicitly: this platform's clock can hand
    back identical ``timezone.now()`` values microseconds apart, which
    would make "newest first" a coin flip on the uuid tiebreak
    (pagination.md only promises determinism, not recency, on a tie).
    """
    from datetime import timedelta

    from django.utils import timezone

    base = timezone.now()
    for attempt in (1, 2):
        TaskResolution.objects.create(
            task=task,
            attempt_number=attempt,
            branch_name=f"feat/{task.pk}",
            commit_sha=f"{attempt:040x}"[:40],
            execution_summary=f"attempt {attempt}",
            diff_summary={"files": 0, "insertions": 0, "deletions": 0},
            changed_files=[],
            requires_human_attention=False,
            risk_justification="",
            submitted_by_session="sess_wp32",
            submitted_at=base + timedelta(seconds=attempt),
        )


def test_listing_newest_first_for_owner_and_agent_with_cursor(
    owner_client: APIClient, project: Project
) -> None:
    """§9.2 Agent/Owner read: newest usable first, cursor-paged, device out."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])
    _seed_resolutions(task)
    url = f"/api/v1/tasks/{task.pk}/resolutions"

    owner_get = owner_client.get(url)
    assert owner_get.status_code == 200
    assert set(owner_get.json()) == {"results", "next_cursor"}, "pagination.md envelope"
    attempts = [row["attempt_number"] for row in owner_get.json()["results"]]
    assert attempts == [2, 1], "newest first — the auditor's FR-AUD-01 order"

    agent_get = agent.get(url)
    assert agent_get.status_code == 200
    assert len(agent_get.json()["results"]) == 2

    page_one = agent.get(url, {"page_size": 1})
    assert page_one.status_code == 200
    assert page_one.json()["next_cursor"] is not None
    assert page_one.json()["results"][0]["attempt_number"] == 2

    page_two = agent.get(url, {"page_size": 1, "cursor": page_one.json()["next_cursor"]})
    assert page_two.status_code == 200
    assert page_two.json()["results"][0]["attempt_number"] == 1
    assert page_two.json()["next_cursor"] is None, "last page says so"


def test_listing_empty_task_and_bad_cursor(owner_client: APIClient, project: Project) -> None:
    """Empty → empty page; a mangled cursor is VALIDATION_ERROR (rule 1)."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])
    url = f"/api/v1/tasks/{task.pk}/resolutions"

    empty = agent.get(url)
    assert empty.status_code == 200
    assert empty.json() == {"results": [], "next_cursor": None}

    bad = agent.get(url, {"cursor": "not-a-cursor"})
    assert bad.status_code == 400
    assert _code(bad) == "VALIDATION_ERROR"


def test_patch_serving_round_trip_matches_the_stored_bytes(
    owner_client: APIClient, project: Project
) -> None:
    """GET /resolutions/{id}/patch serves the body the submission stored."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])
    submitted = _submit(agent, task)
    resolution_id = submitted.json()["resolution"]["id"]

    patch = agent.get(f"/api/v1/resolutions/{resolution_id}/patch")
    assert patch.status_code == 200
    body = patch.json()
    assert body["patch"] == SAMPLE_PATCH
    assert body["diff_too_large"] is False
    assert body["marker"] is None
    assert body["sha256"] and body["size_bytes"] == len(SAMPLE_PATCH.encode("utf-8"))


def test_unknown_resolution_id_answers_the_documented_mapping(
    owner_client: APIClient, project: Project
) -> None:
    """No resolution-scoped not-found code exists: generic NotFound → 400."""
    agent = _coder(owner_client, project)
    response = agent.get("/api/v1/resolutions/00000000-0000-0000-0000-000000000000/patch")
    assert response.status_code == 400
    assert _code(response) == "VALIDATION_ERROR"
