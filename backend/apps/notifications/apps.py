"""App registration for the ``notifications`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Push dispatch, dedupe, delivery tracking (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self) -> None:
        """Install the push dispatch on the review-push seam (MT-5.4-01).

        The events/attachments app-config precedent for hook
        installation: one registration, one code path. The seam is
        skipped in the unit layer and when push is disabled — see
        :func:`ensure_push_dispatch_wired` for both gates.
        """
        from .dispatch import ensure_push_dispatch_wired

        ensure_push_dispatch_wired()
