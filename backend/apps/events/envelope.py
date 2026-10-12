"""The Section 9.6 event envelope — one row, one wire shape (MT-1.9-01).

Single projection from a stored :class:`apps.events.models.Event` row to
the exact JSON object Section 9.6 defines: seven keys — ``id``, ``type``,
``project_id``, ``task_id``, ``occurred_at``, ``actor``, ``data`` — with
``actor`` re-grouped into the structured ``{"type", "ref"}`` object and
``occurred_at`` rendered as the plan's second-precision UTC instant
(``2026-10-11T12:45:02Z``).

The publisher (MT-1.9-03) and the tests share this function, so the
published payload and the stored row can never drift apart: what the SSE
gateway (WP-1.10) streams is what the table holds. The Section 12.5
``correlation_id`` stays a column, never an envelope key — Section 9.6's
list is closed (Section 20.5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .models import Event


def event_envelope(event: Event) -> dict[str, Any]:
    """Return *event* as the exact Section 9.6 envelope object."""
    return {
        "id": event.pk,
        "type": event.type,
        "project_id": event.project_id,
        "task_id": event.task_id,
        "occurred_at": _iso_utc_z(event.occurred_at),
        "actor": {"type": event.actor_type, "ref": event.actor_ref},
        "data": event.data,
    }


def _iso_utc_z(value: datetime) -> str:
    """Render *value* as the plan's ``YYYY-MM-DDTHH:MM:SSZ`` UTC instant."""
    return value.astimezone(UTC).isoformat(timespec="seconds", sep="T").replace("+00:00", "Z")
