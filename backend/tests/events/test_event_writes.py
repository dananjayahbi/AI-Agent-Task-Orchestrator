"""MT-1.9-02 — the write-in-transaction helper and its wired call sites.

Proves the Section 19 WP-1.9 acceptance for everything wired so far:

* every legal transition writes **exactly one** Event row in the same
  transaction as the state change (through the single dispatcher seam);
* every wired emission site of M1-up-to-WP-1.9 — task create/update
  (WP-1.4), project create (WP-1.3), project/policy update (WP-1.3) —
  writes exactly one event with the correct Section 9.6 envelope;
* a forced rollback leaves **zero** Event rows behind (event and change
  commit or roll back together — Section 9.3);
* the helper refuses types outside the Section 9.6 catalog before any
  row exists (catalog-first, Section 20.4 item 5) and fills the
  Section 12.5 correlation id from explicit → request scope → generated;
* the helper performs no network side effects while the transaction is
  open (publishing is MT-1.9-03's post-commit concern, asserted in
  ``test_post_commit_publish.py``).

Token actions (issuance/revocation/login — Section 12.5) are **not**
wired here: the Section 9.6 catalog has no token/login type and
inventing one is out of bounds; the gap is recorded as OQ-16 and listed
in ``test_event_catalog.py``'s pending set.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from django.core.cache import cache
from django.db import transaction
from rest_framework.test import APIClient

from apps.core.correlation import reset_correlation_id, set_correlation_id
from apps.events.models import Event
from apps.events.services import write_event
from apps.projects.services.projects import create_project
from apps.tasks.models import TaskTransition
from apps.tasks.services.tasks import create_task, update_task
from apps.tasks.state_machine.dispatcher import dispatch_transition
from tests.wp15_helpers import make_project, make_task

PASSWORD = "event-writes-tests-1!"  # pragma: allowlist secret


def _write_helper(**overrides: Any) -> Event:
    """One helper call with canonical defaults (shared by the tests below)."""
    payload: dict[str, Any] = {
        "type": "task.transitioned",
        "project_id": "PID00001",
        "task_id": "PID00001-T001",
        "actor_type": "system",
        "actor_ref": "lease-sweeper",
        "data": {"reason_code": "lease_expired"},
    }
    payload.update(overrides)
    return write_event(**payload)


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Login throttling is process state — keep budgets fresh across files."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport), same as WP-1.3's suite."""
    from apps.accounts.models import User

    User.objects.create_user("owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


# --- the helper itself ------------------------------------------------------


def test_helper_writes_one_row_with_the_full_envelope_fields(db: None) -> None:
    """One call → one row with the Section 9.6 envelope + correlation id."""
    event = _write_helper()

    assert Event.objects.count() == 1
    assert event.type == "task.transitioned"
    assert event.project_id == "PID00001"
    assert event.task_id == "PID00001-T001"
    assert event.actor_type == "system"
    assert event.actor_ref == "lease-sweeper"
    assert event.data == {"reason_code": "lease_expired"}
    assert event.occurred_at is not None
    assert event.correlation_id, "Section 12.5: the column is never empty"


def test_correlation_id_resolves_explicit_then_scope_then_generated(
    db: None,
) -> None:
    """Section 12.5: explicit value wins, then request scope, then fresh id."""
    explicit = _write_helper(correlation_id="corr-explicit")
    assert explicit.correlation_id == "corr-explicit"

    token = set_correlation_id("corr-request-scope")
    try:
        in_scope = _write_helper()
    finally:
        reset_correlation_id(token)
    assert in_scope.correlation_id == "corr-request-scope"

    generated = _write_helper()
    assert generated.correlation_id
    assert generated.correlation_id != "corr-request-scope"


def test_unknown_catalog_type_is_refused_before_any_row(db: None) -> None:
    """Catalog-first (Section 20.4 item 5): no type, no write, no guess."""
    with pytest.raises(ValueError, match="Section 9.6 catalog"):
        _write_helper(type="token.issued")

    assert Event.objects.count() == 0


def test_non_canonical_actor_is_refused_before_any_row(db: None) -> None:
    """Actor triad (Section 7.2) checked at the writer, not just the DB."""
    with pytest.raises(ValueError, match="owner/agent/system"):
        _write_helper(actor_type="robot")
    with pytest.raises(ValueError, match="actor_ref"):
        _write_helper(actor_ref="   ")

    assert Event.objects.count() == 0


def test_helper_rollback_leaves_no_event_row(db: None) -> None:
    """Forced rollback → the event disappears with the transaction."""
    with pytest.raises(RuntimeError, match="forced rollback"), transaction.atomic():
        _write_helper()
        raise RuntimeError("forced rollback")

    assert Event.objects.count() == 0


# --- transitions: exactly one event per dispatch ----------------------------


def test_transition_dispatch_writes_exactly_one_event_row(db: None) -> None:
    """The dispatcher seam: one legal transition → exactly one Event row."""
    project = make_project(name="Event writes")
    task = make_task(project, 1)

    result = dispatch_transition(
        task_id=task.pk,
        trigger="publish",
        actor_type="owner",
        actor_ref="user:1",
        note="emit me",
    )

    events = Event.objects.filter(task_id=task.pk)
    assert events.count() == 1, "exactly one event per transition (Section 19.1)"
    event = events.get()
    assert event.type == "task.transitioned"
    assert (event.actor_type, event.actor_ref) == ("owner", "user:1")
    assert event.project_id == project.pk
    assert event.data == {
        "from_state": "draft",
        "to_state": "pending",
        "reason_code": "publish",
        "task_version": result.version,
    }
    assert event.correlation_id, "generated outside a request scope (Section 12.5)"


def test_rollback_takes_the_transition_and_event_together(db: None) -> None:
    """Forced failure after the dispatch: state, history and event all gone."""
    project = make_project(name="Event rollback")
    task = make_task(project, 1)

    with pytest.raises(RuntimeError, match="forced rollback"), transaction.atomic():
        dispatch_transition(
            task_id=task.pk,
            trigger="publish",
            actor_type="owner",
            actor_ref="user:1",
        )
        raise RuntimeError("forced rollback")

    task.refresh_from_db()
    assert task.state == "draft", "the dispatch rolled back as one unit"
    assert task.version == 1
    assert Event.objects.count() == 0, "no event survives the rolled-back transaction"
    assert TaskTransition.objects.filter(task=task).count() == 0


# --- task CRUD call sites ---------------------------------------------------


def test_task_create_emits_exactly_one_task_created(db: None) -> None:
    """WP-1.4's creating transaction now carries T1's Section 9.6 event."""
    project = make_project(name="Task create event")

    task = create_task(project=project, title="Ship it", created_by="user:7")

    events = Event.objects.filter(task_id=task.pk)
    assert events.count() == 1
    event = events.get()
    assert event.type == "task.created"
    assert (event.actor_type, event.actor_ref) == ("owner", "user:7")
    assert event.data == {"task_version": 1}
    assert event.project_id == project.pk


def test_task_create_without_user_context_falls_back_to_the_role_label(
    db: None,
) -> None:
    """Direct service calls carry no user id — the label keeps actor honest."""
    project = make_project(name="Task create no-user")

    task = create_task(project=project, title="No user", created_by=None)

    event = Event.objects.get(task_id=task.pk)
    assert (event.actor_type, event.actor_ref) == ("owner", "owner")


def test_task_update_emits_exactly_one_task_updated(db: None) -> None:
    """FR-TSK-06 change → one `task.updated` naming the applied fields."""
    project = make_project(name="Task update event")
    task = make_task(project, 1)

    updated = update_task(
        task=task,
        validated={"title": "Renamed", "priority": "high"},
        expected_version=1,
        actor_ref="user:7",
    )

    events = Event.objects.filter(task_id=task.pk)
    assert events.count() == 1
    event = events.get()
    assert event.type == "task.updated"
    assert (event.actor_type, event.actor_ref) == ("owner", "user:7")
    assert event.data == {
        "task_version": updated.version,
        "fields": ["priority", "title"],
    }


def test_task_update_without_changes_writes_no_event(db: None) -> None:
    """No change → no version bump → no state change → no event (9.6)."""
    project = make_project(name="Task update no-op")
    task = make_task(project, 1)

    result = update_task(task=task, validated={}, expected_version=1)

    assert result.version == 1
    assert Event.objects.filter(task_id=task.pk).count() == 0


# --- project call sites (service + API paths) -------------------------------


def test_project_create_emits_exactly_one_project_created(db: None) -> None:
    """WP-1.3's creating transaction carries the Section 9.6 event."""
    project = create_project(
        name="Event project",
        repo_path="/srv/repos/event-project",
        default_branch="main",
        actor_ref="user:9",
    )

    events = Event.objects.filter(project_id=project.pk)
    assert events.count() == 1
    event = events.get()
    assert event.type == "project.created"
    assert (event.actor_type, event.actor_ref) == ("owner", "user:9")
    assert event.task_id is None, "project-level event carries no task id"


def test_project_patch_via_api_emits_project_updated(db: None, owner_client: APIClient) -> None:
    """The view-level PATCH writes `project.updated` in the same transaction."""
    created = _create_project(owner_client)
    before = Event.objects.filter(project_id=created["id"]).count()
    assert before == 1, "the POST already emitted project.created"

    response = owner_client.patch(f"/api/v1/projects/{created['id']}", {"name": "Renamed project"})
    assert response.status_code == 200, response.content

    events = Event.objects.filter(project_id=created["id"]).order_by("id")
    assert events.count() == before + 1, "exactly one event per PATCH"
    event = events.last()
    assert event is not None
    assert event.type == "project.updated"
    assert event.actor_type == "owner"
    assert event.actor_ref != "owner", "the API path carries the session user id"
    assert event.data == {"scope": "project", "fields": ["name"]}


def test_policy_patch_via_api_emits_project_updated_with_policy_scope(
    db: None, owner_client: APIClient
) -> None:
    """Section 12.5 policy edit: `project.updated` + policy scope discriminator.

    There is no `policy.updated` catalog type — the closed Section 9.6
    list covers the edit as `project.updated` (catalog-first; OQ-16 keeps
    the question visible without inventing a type).
    """
    created = _create_project(owner_client)

    response = owner_client.patch(f"/api/v1/projects/{created['id']}/policy", {"max_retries": 5})
    assert response.status_code == 200, response.content

    event = Event.objects.filter(project_id=created["id"], type="project.updated").last()
    assert event is not None, "the policy edit is in the audit trail (12.5)"
    assert event.data == {"scope": "policy", "fields": ["max_retries"]}
    assert event.actor_ref != "owner", "actor is the logged-in owner"


def _create_project(owner_client: APIClient) -> Any:
    """POST a valid project; return the parsed 201 body."""
    response = owner_client.post(
        "/api/v1/projects",
        {
            "name": "Event emission project",
            "repo_path": "/srv/repos/event-emission",
            "default_branch": "main",
        },
    )
    assert response.status_code == 201, response.content
    return cast(dict[str, Any], response.json())
