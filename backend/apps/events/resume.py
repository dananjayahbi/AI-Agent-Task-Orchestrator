"""Lossless resume via Last-Event-ID (Sections 9.6, 9.2; MT-1.10-03).

Section 9.6: "reconnecting clients send the last id and receive missed
events, then switch to live (no gaps, no duplicates)." Two halves:

* **Reading the client's last id** — the SSE standard's ``Last-Event-ID``
  header (what a browser ``EventSource`` re-sends automatically on
  reconnect) *and* a ``last_event_id`` query parameter, because browser
  ``EventSource`` cannot set arbitrary headers in every environment
  (MT-4.3-04's risk note: the plan mandates resume behavior, not the
  transport mechanism — both spellings are accepted and the choice is
  recorded in the WP changelog). Empty header = fresh connection. A
  non-integer value is client input: ``VALIDATION_ERROR`` (Section 9.2),
  rejected before any stream opens. A fresh connection starts **live**
  without backfill (documented reading — the plan does not mandate initial
  backfill; the audit-log *history* endpoint exists for browsing).
* **Replay** — all stored rows with ``id`` greater than the client's last,
  filtered by the connection's ``project``/``task`` filters, in ``id``
  order, then live. The gap-free handover is a property of the
  registration order in ``views.get``: the connection joins the hub
  *before* the replay query runs, so every concurrently published event is
  either in the replay result or in the live queue — and the connection's
  ``claim`` gate (fanout.py) delivers each id exactly once no matter which
  copy arrives second (the race test in tests/events/test_resume.py pins
  this).

Replay assumes history retention (OQ-10's 1-year default); a client whose
last id predates retention simply replays from the oldest retained row —
full-restart semantics were not specified by the plan and are not invented
here (MT-1.10-03 risk note).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rest_framework.exceptions import ValidationError

from .envelope import event_envelope
from .models import Event

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from .fanout import StreamConnection


def last_event_id_from(request: Any) -> int | None:
    """The client's last received event id, or ``None`` for a fresh stream.

    Header first (the SSE standard), then the query parameter (fetch/mobile
    clients that cannot set the header). Blank/absent = ``None``; a value
    that is not a non-negative integer raises the canonical
    ``VALIDATION_ERROR`` (Section 9.2; Section 20.4 item 5).
    """
    raw = request.headers.get("Last-Event-ID") or request.query_params.get("last_event_id")
    if raw is None or str(raw).strip() == "":
        return None
    text = str(raw).strip()
    if not text.isdigit():
        raise ValidationError({"last_event_id": "Must be a non-negative integer event id."})
    return int(text)


def missed_envelopes(last_event_id: int, connection: StreamConnection) -> list[dict[str, Any]]:
    """Stored rows the client missed: ``id > last_event_id``, filtered, ascending.

    Synchronous (ORM) — the stream generator calls it through
    ``sync_to_async`` (thread-sensitive, the request's own thread). The
    connection's connect-time filters and scope narrow the query
    (index-backed: ``(project_id, id)`` / ``(task_id, id)``, MT-1.9-01);
    the ``connection.accepts`` pass is the per-event authorization belt of
    MT-1.10-05 applied identically on this path. Rows are returned in
    ``id`` order — the total order Section 9.6 defines for replay.
    """
    queryset = Event.objects.filter(id__gt=last_event_id)
    if connection.scope.project_id is not None:
        queryset = queryset.filter(project_id=connection.scope.project_id)
    if connection.project is not None:
        queryset = queryset.filter(project_id=connection.project)
    if connection.task is not None:
        queryset = queryset.filter(task_id=connection.task)
    envelopes: list[dict[str, Any]] = []
    for row in queryset.order_by("id"):
        envelope = event_envelope(row)
        if connection.accepts(envelope):
            envelopes.append(envelope)
    return envelopes


__all__ = ["last_event_id_from", "missed_envelopes"]
