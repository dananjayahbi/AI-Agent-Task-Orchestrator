"""The write-in-transaction event helper (MT-1.9-02; Sections 9.6, 12.5, 9.3).

``write_event`` is the single API through which every module appends an
Event row, and the guarantees of Section 9.6/19.1 live here:

* **Same transaction as the change.** The row joins the caller's open
  ``transaction.atomic()`` block — a rollback takes the event with it
  (Section 9.3's claim flow writes Transition and Event rows inside one
  transaction; the dispatcher's hook calls this inside its own).
* **Exactly one row per action.** One call, one row — duplication is a
  wiring bug the catalog tests pin (MT-1.9-05).
* **No side effects while the transaction is open.** The helper only
  writes the row; the publish itself runs strictly after commit via
  ``transaction.on_commit`` (MT-1.9-03) — never inline, never while the
  transaction is open.
* **Catalog-first.** A ``type`` outside the Section 9.6 list is a
  ``ValueError`` (programmer error, never a silent write — Section 20.4
  item 5); the table's CheckConstraint enforces the same closed set at
  the database.
* **Section 12.5 fields.** Every row carries the actor and a correlation
  id: an explicit one, else the request scope's
  (``apps.core.correlation``), else a freshly generated id so the column
  is never empty outside a request (documented reading, WP changelog).

``write_transition_event`` is the adapter registered as the state
machine's default in-transaction hook (``EventsConfig.ready()`` →
``set_default_event_hook``): it accepts the exact payload shape the
dispatcher builds — ``type``, ``project_id``, ``task_id``,
``occurred_at``, ``actor{type,ref}``, ``data`` — and routes it through
the same writer, so transitions and every other emission site share one
code path.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.core.correlation import get_correlation_id, new_correlation_id

from .catalog import EVENT_TYPES
from .models import Event, EventActorType
from .publisher import publish_event


def write_event(
    *,
    type: str,
    project_id: str,
    actor_type: str,
    actor_ref: str,
    task_id: str | None = None,
    data: Mapping[str, Any] | None = None,
    occurred_at: datetime | None = None,
    correlation_id: str | None = None,
) -> Event:
    """Append one Event row to the caller's open transaction.

    ``occurred_at`` defaults to the server clock *at call time*, inside
    the transaction (principle P7); pass an explicit instant only when
    the emission site already stamped one (the dispatcher does).
    ``correlation_id`` resolves explicit → request scope → generated.
    Publishing is registered separately, post-commit (MT-1.9-03).
    """
    if type not in EVENT_TYPES:
        raise ValueError(
            f"event type {type!r} is not in the Section 9.6 catalog — "
            "amend the catalog in the plan first (Section 20.4 item 5)."
        )
    if actor_type not in EventActorType.values:
        raise ValueError(f"actor_type {actor_type!r} is not owner/agent/system (Section 7.2).")
    if not actor_ref.strip():
        raise ValueError("actor_ref must identify the actor (Section 12.5).")
    if not project_id.strip():
        raise ValueError("project_id is required (Section 9.6 envelope).")

    event: Event = Event.objects.create(
        type=type,
        project_id=project_id,
        task_id=task_id or None,
        occurred_at=occurred_at if occurred_at is not None else timezone.now(),
        actor_type=actor_type,
        actor_ref=actor_ref,
        data=dict(data or {}),
        correlation_id=correlation_id or get_correlation_id() or new_correlation_id(),
    )
    # MT-1.9-03: strictly post-commit (Section 9.6) — deferred while the
    # caller's transaction is open, discarded entirely on rollback; the
    # publish itself can never fail this request (publisher swallows).
    transaction.on_commit(lambda: publish_event(event))
    return event


def write_transition_event(payload: Mapping[str, Any]) -> None:
    """State-machine seam adapter: dispatcher payload → :func:`write_event`.

    Typed to ``apps.tasks.state_machine.hooks.EventHook`` — installed as
    the default in-transaction writer by ``EventsConfig.ready()``. The
    dispatcher validates actor/reason/catalog itself; this adapter only
    unwraps the envelope shape.
    """
    actor = payload["actor"]
    write_event(
        type=payload["type"],
        project_id=payload["project_id"],
        task_id=payload.get("task_id"),
        actor_type=actor["type"],
        actor_ref=actor["ref"],
        data=payload.get("data"),
        occurred_at=payload.get("occurred_at"),
    )
