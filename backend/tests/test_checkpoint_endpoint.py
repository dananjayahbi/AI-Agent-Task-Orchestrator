"""MT-1.8-03 — ``POST /tasks/{id}/checkpoints`` (Section 9.2 Progress row;
Section 6.5 Flow B; Section 10.5 ``log_task_checkpoint``; NFR-11/12).

Run with ``pytest backend/tests -k checkpoint_endpoint -q``. Every
case runs against the **real** route with real credentials:

* the success shape — the stored checkpoint's identity plus the **new
  ``lease_expires_at``** (Section 10.5: "Returns new expiry") and
  ``capped`` (MT-1.6-03's flag, consumed here so the bridge can surface
  submit-or-release guidance);
* validation refusals with ``VALIDATION_ERROR`` — ``percent`` out of
  0-100, unknown ``kind``, missing fencing pair, unknown fields
  (StrictSerializerMixin);
* the lease refusals through the API — expired (409
  ``LEASE_EXPIRED``, the bridge's "stop and re-claim" signal), stale
  generation, foreign session (403 ``LEASE_NOT_OWNED``), cross-project
  token (403 ``AUTH_FORBIDDEN_PROJECT``), unknown task (404
  ``TASK_NOT_FOUND``);
* ``Idempotency-Key`` replay: the same request replays the stored
  outcome — **no duplicate row, no double extension** (NFR-12);
* the ``task.checkpoint`` event row (Section 9.6, Section 20.4 item 6)
  with the feed payload G-11's consumers render;
* the hard cap end-to-end (WP-1.8 acceptance).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.events.models import Event
from apps.projects.models import Project
from apps.tasks.models import Task, TaskCheckpoint

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    PASSWORD,
    active_policy_project,
    claim,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db

CHECKPOINT_FIELDS = {
    "id",
    "task_id",
    "attempt_number",
    "session_id",
    "timestamp",
    "message",
    "percent",
    "token_usage",
    "kind",
}


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — fresh budget per test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (cookie transport) for token minting."""
    User.objects.create_user("owner-wp18", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner-wp18", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


def issue_agent_token(owner_client: APIClient, project_id: str, *scopes: str) -> dict[str, Any]:
    """Mint a project-scoped agent token through the real Owner API."""
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": list(scopes)}
    )
    assert response.status_code == 201, response.content
    return dict(response.json())


def agent_client(token_payload: dict[str, Any]) -> APIClient:
    """A plain client carrying one agent bearer token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_payload['token']}")
    return client


def _code(response: Any) -> str:
    """The catalog code of one standard envelope (five fields, asserted)."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])


def _claimed(
    owner_client: APIClient, project: Project, *, index: int = 1, **policy_fields: Any
) -> tuple[APIClient, Task]:
    """An agent client holding a live lease on one task (the Flow B caller)."""
    if policy_fields:
        from apps.projects.models import ProjectPolicy

        ProjectPolicy.objects.filter(pk=project.agent_policy_id).update(**policy_fields)
        project.agent_policy.refresh_from_db()
    task = make_pending_task(project, index)
    claim(task, session_id="sess_ep18")
    task.refresh_from_db()
    return agent_client(issue_agent_token(owner_client, project.pk, "coder")), task


def checkpoint_body(**overrides: Any) -> dict[str, Any]:
    """A valid ``CheckpointCreate`` body (the fencing pair of the holder)."""
    body: dict[str, Any] = {
        "session_id": "sess_ep18",
        "lease_generation": 1,
        "message": "halfway",
        "percent": 50,
    }
    body.update(overrides)
    return body


# --- success: the frozen response contract (Section 10.5) -------------------


def test_valid_checkpoint_returns_identity_and_new_expiry(
    owner_client: APIClient, project: Project
) -> None:
    """200 body: checkpoint identity + the new lease_expires_at (7.2 fields)."""
    client, task = _claimed(owner_client, project)
    # Same Windows ~15.6 ms clock-tick caveat recorded in
    # test_checkpoint_ownership: a claim and a checkpoint inside one tick
    # compute the same min(now + duration, cap) and the strict comparison
    # below would flake. Start the stored expiry short of now + duration —
    # a correct extension must still move it strictly forward.
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() + timedelta(minutes=1))
    task.refresh_from_db()

    response = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(),
        format="json",
    )

    assert response.status_code == 200, response.content
    body = response.json()
    assert set(body) == {"checkpoint", "lease_extended", "lease_expires_at", "capped"}
    checkpoint = body["checkpoint"]
    assert set(checkpoint) == CHECKPOINT_FIELDS, "Section 7.2 fields, field for field"
    assert checkpoint["task_id"] == task.pk
    assert checkpoint["session_id"] == "sess_ep18"
    assert checkpoint["attempt_number"] == task.attempt_number
    assert checkpoint["message"] == "halfway"
    assert checkpoint["percent"] == 50
    assert checkpoint["kind"] == "progress"
    assert body["lease_extended"] is True
    assert body["capped"] is False
    assert body["lease_expires_at"] is not None
    assert task.lease_expires_at is not None, "a live claim always carries an expiry"
    assert body["lease_expires_at"] > task.lease_expires_at.isoformat(), (
        "the response carries the *new* expiry (Section 10.5)"
    )


def test_valid_checkpoint_persists_row_touch_and_lease(
    owner_client: APIClient, project: Project
) -> None:
    """The response mirrors committed state: row, touch, extension."""
    client, task = _claimed(owner_client, project)

    response = client.post(f"/api/v1/tasks/{task.pk}/checkpoints", checkpoint_body(), format="json")

    assert TaskCheckpoint.objects.filter(task=task).count() == 1
    fresh = Task.objects.get(pk=task.pk)
    row = TaskCheckpoint.objects.get(task=task)
    assert fresh.last_checkpoint_at == row.timestamp
    assert fresh.lease_expires_at is not None
    assert fresh.lease_expires_at.isoformat()[:19] >= response.json()["lease_expires_at"][:19]


def test_checkpoint_event_row_is_written(owner_client: APIClient, project: Project) -> None:
    """Section 9.6: one ``task.checkpoint`` event with the feed payload."""
    client, task = _claimed(owner_client, project)

    client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(token_usage={"input_tokens": 1200}),
        format="json",
    )

    event = Event.objects.get(type="task.checkpoint")
    assert event.task_id == task.pk
    assert event.project_id == project.pk
    assert event.actor_type == "agent"
    assert event.actor_ref == "sess_ep18"
    data = event.data
    assert data["kind"] == "progress"
    assert data["percent"] == 50
    assert data["message"] == "halfway"
    assert data["token_usage"] == {"input_tokens": 1200}
    assert data["checkpoint_id"] == str(TaskCheckpoint.objects.get(task=task).pk)


def test_percent_and_kind_validate_at_the_boundary(
    owner_client: APIClient, project: Project
) -> None:
    """Out-of-range percent and unknown kind answer VALIDATION_ERROR (400)."""
    client, task = _claimed(owner_client, project)

    over = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints", checkpoint_body(percent=101), format="json"
    )
    assert over.status_code == 400
    assert _code(over) == "VALIDATION_ERROR"

    negative = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints", checkpoint_body(percent=-1), format="json"
    )
    assert negative.status_code == 400
    assert _code(negative) == "VALIDATION_ERROR"

    unknown_kind = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints", checkpoint_body(kind="ping"), format="json"
    )
    assert unknown_kind.status_code == 400
    assert _code(unknown_kind) == "VALIDATION_ERROR"

    assert not TaskCheckpoint.objects.filter(task=task).exists(), "no partial writes"


def test_percent_bounds_edges_are_accepted(owner_client: APIClient, project: Project) -> None:
    """0 and 100 store; null stores (Section 7.2 boundaries)."""
    client, task = _claimed(owner_client, project)

    for percent in (0, 100, None):
        response = client.post(
            f"/api/v1/tasks/{task.pk}/checkpoints",
            checkpoint_body(percent=percent),
            format="json",
        )
        assert response.status_code == 200, response.content

    assert TaskCheckpoint.objects.filter(task=task).count() == 3


def test_missing_fencing_pair_is_a_validation_error(
    owner_client: APIClient, project: Project
) -> None:
    """No session or generation: the boundary refuses before the gate."""
    client, task = _claimed(owner_client, project)

    no_session = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        {"lease_generation": 1, "message": "x"},
        format="json",
    )
    assert no_session.status_code == 400
    assert _code(no_session) == "VALIDATION_ERROR"

    no_generation = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        {"session_id": "sess_ep18", "message": "x"},
        format="json",
    )
    assert no_generation.status_code == 400
    assert _code(no_generation) == "VALIDATION_ERROR"


def test_unknown_fields_are_refused(owner_client: APIClient, project: Project) -> None:
    """StrictSerializerMixin: ``attempt_number``/``timestamp`` are server-set."""
    client, task = _claimed(owner_client, project)

    response = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(attempt_number=9, timestamp="2026-01-01T00:00:00Z"),
        format="json",
    )

    assert response.status_code == 400
    assert _code(response) == "VALIDATION_ERROR"


# --- the lease refusals through the API (MT-1.8-02, proven end-to-end) -----


def test_expired_lease_answers_lease_expired_and_writes_nothing(
    owner_client: APIClient, project: Project
) -> None:
    """409 LEASE_EXPIRED — the bridge's "stop and re-claim" signal (10.5)."""
    client, task = _claimed(owner_client, project)
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))
    task.refresh_from_db()

    response = client.post(f"/api/v1/tasks/{task.pk}/checkpoints", checkpoint_body(), format="json")

    assert response.status_code == 409
    assert _code(response) == "LEASE_EXPIRED"
    assert not TaskCheckpoint.objects.filter(task=task).exists()
    assert not Event.objects.filter(type="task.checkpoint").exists()
    fresh = Task.objects.get(pk=task.pk)
    assert fresh.last_checkpoint_at is None
    assert fresh.version == task.version, "a refusal writes nothing"


def test_stale_generation_answers_lease_expired(owner_client: APIClient, project: Project) -> None:
    """ADR-012 through the API: a previous generation is LEASE_EXPIRED."""
    client, task = _claimed(owner_client, project)

    response = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(lease_generation=task.lease_generation - 1),
        format="json",
    )

    assert response.status_code == 409
    assert _code(response) == "LEASE_EXPIRED"
    assert not TaskCheckpoint.objects.filter(task=task).exists()


def test_foreign_session_answers_lease_not_owned(owner_client: APIClient, project: Project) -> None:
    """403 LEASE_NOT_OWNED: a different session on a live lease."""
    client, task = _claimed(owner_client, project)

    response = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(session_id="sess_intruder"),
        format="json",
    )

    assert response.status_code == 403
    assert _code(response) == "LEASE_NOT_OWNED"
    assert not TaskCheckpoint.objects.filter(task=task).exists()


def test_cross_project_token_answers_auth_forbidden_project(
    owner_client: APIClient, project: Project
) -> None:
    """ADR-004 Zero-Bleed: a PID00001 token cannot checkpoint PID00002."""
    _, task = _claimed(owner_client, project)
    other = active_policy_project(pid="PID00002")
    other_client = agent_client(issue_agent_token(owner_client, other.pk, "coder"))

    response = other_client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints", checkpoint_body(), format="json"
    )

    assert response.status_code == 403
    assert _code(response) == "AUTH_FORBIDDEN_PROJECT"
    assert not TaskCheckpoint.objects.filter(task=task).exists()


def test_unknown_task_answers_task_not_found(owner_client: APIClient, project: Project) -> None:
    """Well-formed but unknown id: TASK_NOT_FOUND (404)."""
    client, _ = _claimed(owner_client, project)

    response = client.post(
        f"/api/v1/tasks/{project.pk}-T777/checkpoints", checkpoint_body(), format="json"
    )

    assert response.status_code == 404
    assert _code(response) == "TASK_NOT_FOUND"


def test_anonymous_caller_is_refused(owner_client: APIClient, project: Project) -> None:
    """No credential: AUTH_REQUIRED (401), never a silent write."""
    _, task = _claimed(owner_client, project)
    anonymous = APIClient()

    response = anonymous.post(
        f"/api/v1/tasks/{task.pk}/checkpoints", checkpoint_body(), format="json"
    )

    assert response.status_code == 401
    assert _code(response) == "AUTH_REQUIRED"
    assert not TaskCheckpoint.objects.filter(task=task).exists()


def test_owner_session_cannot_checkpoint(owner_client: APIClient, project: Project) -> None:
    """The POST cell is Agent (MT-1.8-03) — an owner session is refused."""
    _, task = _claimed(owner_client, project)

    response = owner_client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints", checkpoint_body(), format="json"
    )

    assert response.status_code == 403
    assert _code(response) == "ROLE_NOT_PERMITTED"
    assert not TaskCheckpoint.objects.filter(task=task).exists()


# --- idempotency (NFR-12; ADR-012) ------------------------------------------


def test_idempotent_replay_returns_the_same_outcome_without_duplicate_writes(
    owner_client: APIClient, project: Project
) -> None:
    """Same key + same request: one row, one extension, byte-identical body."""
    client, task = _claimed(owner_client, project)

    first = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(),
        format="json",
        HTTP_IDEMPOTENCY_KEY="ckpt-key-1",
    )
    assert first.status_code == 200
    task.refresh_from_db()
    extended_expiry = task.lease_expires_at

    second = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(),
        format="json",
        HTTP_IDEMPOTENCY_KEY="ckpt-key-1",
    )

    assert second.status_code == 200
    assert second.json() == first.json(), "the replay is the stored outcome"
    assert TaskCheckpoint.objects.filter(task=task).count() == 1, "no duplicate row"
    task.refresh_from_db()
    assert task.lease_expires_at == extended_expiry, "no double extension"
    assert Event.objects.filter(type="task.checkpoint").count() == 1, "no re-emission"


def test_a_fresh_key_executes_again(owner_client: APIClient, project: Project) -> None:
    """A different key is a different request: a second row is stored."""
    client, task = _claimed(owner_client, project)

    first = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(),
        format="json",
        HTTP_IDEMPOTENCY_KEY="ckpt-key-a",
    )
    second = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(),
        format="json",
        HTTP_IDEMPOTENCY_KEY="ckpt-key-b",
    )

    assert first.status_code == second.status_code == 200
    assert TaskCheckpoint.objects.filter(task=task).count() == 2


# --- the hard cap end-to-end (WP-1.8 acceptance) ----------------------------


def test_extension_never_exceeds_the_hard_cap_end_to_end(
    owner_client: APIClient, project: Project
) -> None:
    """min(now + duration, acquired + cap) — capped=True at the boundary."""
    client, task = _claimed(owner_client, project)
    acquired = timezone.now() - timedelta(minutes=230)
    Task.objects.filter(pk=task.pk).update(lease_acquired_at=acquired)
    task.refresh_from_db()
    cap = acquired + timedelta(minutes=project.agent_policy.lease_max_total_minutes)

    response = client.post(f"/api/v1/tasks/{task.pk}/checkpoints", checkpoint_body(), format="json")

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["capped"] is True
    assert body["lease_expires_at"] is not None
    returned = body["lease_expires_at"]
    assert returned[:19] == cap.isoformat()[:19], "the clamp lands exactly on the cap"


# --- kind gating through the API (OQ-04 recorded reading) -------------------


def test_liveness_checkpoint_does_not_extend_by_default(
    owner_client: APIClient, project: Project
) -> None:
    """checkpoint_only: the row stores, the lease does not move."""
    client, task = _claimed(owner_client, project)
    task.refresh_from_db()
    untouched = task.lease_expires_at

    response = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(kind="liveness"),
        format="json",
    )

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["lease_extended"] is False
    assert body["checkpoint"]["kind"] == "liveness"
    fresh = Task.objects.get(pk=task.pk)
    assert fresh.lease_expires_at == untouched
    assert fresh.last_checkpoint_at is not None, "the row still lands"


def test_liveness_checkpoint_extends_under_the_opt_in_mode(
    owner_client: APIClient, project: Project
) -> None:
    """checkpoint_and_liveness: the ping carries the extension too."""
    client, task = _claimed(owner_client, project, lease_extension_mode="checkpoint_and_liveness")

    response = client.post(
        f"/api/v1/tasks/{task.pk}/checkpoints",
        checkpoint_body(kind="liveness"),
        format="json",
    )

    assert response.status_code == 200, response.content
    assert response.json()["lease_extended"] is True
