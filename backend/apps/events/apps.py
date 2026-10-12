"""App registration for the ``events`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class EventsConfig(AppConfig):
    """Event log, realtime gateway (SSE), replay (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.events"
