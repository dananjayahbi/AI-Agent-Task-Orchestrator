"""URL surface of the events app — ``/api/v1``-prefixed by the root include.

Paths mirror the Section 9.2 Events row verbatim: ``GET /events/stream``
(SSE; resume via last event id) and ``GET /events`` (history, filters).
The explicit ``stream`` path is registered first so the literal wins over
any future sibling prefix (defensive ordering, no path conflict today).
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import EventHistoryView, EventStreamView

urlpatterns: list[URLPattern] = [
    path("events/stream", EventStreamView.as_view(), name="events-stream"),
    path("events", EventHistoryView.as_view(), name="events-history"),
]
