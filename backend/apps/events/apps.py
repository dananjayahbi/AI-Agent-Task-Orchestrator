"""App registration for the ``events`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class EventsConfig(AppConfig):
    """Event log, realtime gateway (SSE), replay (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.events"

    def ready(self) -> None:
        """Register the write helper as the state machine's default hook.

        The dispatcher's single in-transaction seam
        (``apps.tasks.state_machine.hooks``) gets the production writer
        here — one registration, one code path: every transition payload
        becomes exactly one Event row in the dispatch transaction
        (Section 9.6; MT-1.9-02). Test recorders still layer on top with
        ``set_event_hook`` and clear back to this default.
        """
        from apps.tasks.state_machine.hooks import set_default_event_hook

        from .services import write_transition_event

        set_default_event_hook(write_transition_event)
