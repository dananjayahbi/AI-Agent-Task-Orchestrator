"""MT-1.9-03 — publish to the Redis channel, strictly after commit.

Acceptance covered here (Section 9.6; MT-1.9-03):

* a committed event publishes **exactly once** — after the transaction
  commits, never while it is open;
* a rolled-back transaction publishes **nothing** (its callbacks are
  discarded with the rollback);
* the published payload equals the stored row's Section 9.6 envelope —
  the seven keys, unchanged (Section 20.5);
* a Redis outage during publish is logged and never fails the
  originating request: the row stays readable (source of truth for the
  DB-based resume of MT-1.10-03);
* channel configuration comes from the documented env-driven defaults
  (``ORCHESTRATOR_EVENTS_CHANNEL`` / ``ORCHESTRATOR_EVENTS_REDIS_URL`` —
  configuration.md rows; no environment-specific values committed).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from django.conf import settings
from django.db import transaction

from apps.events.envelope import event_envelope
from apps.events.models import Event
from apps.events.services import write_event
from apps.tasks.state_machine.dispatcher import dispatch_transition
from tests.wp15_helpers import make_project, make_task

from .conftest import FakeRedis


def _one_event() -> Event:
    """One helper-written event (canonical owner/project emission)."""
    return write_event(
        type="project.created",
        project_id="PID00001",
        actor_type="owner",
        actor_ref="user:1",
    )


def test_committed_event_publishes_exactly_once_with_the_stored_envelope(
    db: None,
    fake_publisher: FakeRedis,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """After commit: one publish, the configured channel, envelope equality."""
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        event = _one_event()

    assert len(callbacks) == 1, "one on-commit callback per event (9.6)"
    assert len(fake_publisher.messages) == 1, "exactly one publish per committed event"
    channel, message = fake_publisher.messages[0]
    assert channel == settings.EVENTS_CHANNEL, "documented channel default"

    payload = json.loads(message)
    assert set(payload) == {
        "id",
        "type",
        "project_id",
        "task_id",
        "occurred_at",
        "actor",
        "data",
    }, "Section 9.6 envelope keys, unchanged"
    stored = Event.objects.get(pk=event.pk)
    assert payload == event_envelope(stored), "published payload == stored row"


def test_publish_is_registered_but_deferred_while_the_transaction_is_open(
    db: None,
    fake_publisher: FakeRedis,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """Nothing goes out inside the open transaction — only the hook is set."""
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        with transaction.atomic():
            _one_event()
            assert fake_publisher.messages == [], "never publish inside the txn"

    assert len(callbacks) == 1, "the callback waits for commit"
    assert fake_publisher.messages == [], "still nothing until the commit runs"


def test_rolled_back_transaction_publishes_nothing(
    db: None,
    fake_publisher: FakeRedis,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """Rollback discards the row and its publish together (Section 9.6)."""
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with pytest.raises(RuntimeError, match="forced rollback"), transaction.atomic():
            _one_event()
            raise RuntimeError("forced rollback")

    assert callbacks == [], "the callback died with the transaction"
    assert fake_publisher.messages == []
    assert Event.objects.count() == 0, "row and publish share one fate"


def test_redis_outage_is_logged_and_never_fails_the_committed_write(
    db: None,
    fake_publisher: FakeRedis,
    django_capture_on_commit_callbacks: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Outage → warning + swallowed; the committed row remains readable."""
    fake_publisher.fail = True

    with (
        django_capture_on_commit_callbacks(execute=True),
        caplog.at_level(logging.WARNING, logger="apps.events.publisher"),
    ):
        event = _one_event()  # must not raise, even when publish explodes

    assert Event.objects.filter(pk=event.pk).exists(), "row survives as source of truth"
    assert fake_publisher.messages == []
    assert any("post-commit publish failed" in record.message for record in caplog.records), (
        "the failure is logged (Section 17), not raised"
    )


def test_channel_configuration_is_the_documented_env_default() -> None:
    """Section 9.10: canonical names with committed defaults, no env values."""
    assert settings.EVENTS_CHANNEL == "orchestrator:events"
    assert settings.EVENTS_REDIS_URL.startswith(("redis://", "rediss://")), (
        "publish URL resolves to a Redis endpoint (defaults to the cache URL)"
    )


def test_transition_dispatch_triggers_one_post_commit_publish(
    db: None,
    fake_publisher: FakeRedis,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """The dispatcher seam flows through the same publish contract (9.6)."""
    project = make_project(name="Publish dispatch")
    task = make_task(project, 1)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        dispatch_transition(
            task_id=task.pk,
            trigger="publish",
            actor_type="owner",
            actor_ref="user:1",
        )

    assert len(callbacks) == 1, "one event row → one publish"
    assert len(fake_publisher.messages) == 1
    _, message = fake_publisher.messages[0]
    payload = json.loads(message)
    assert payload["type"] == "task.transitioned"
    assert payload["task_id"] == task.pk
    assert payload["id"] == Event.objects.get(task_id=task.pk).pk, "SSE id is the row id"
