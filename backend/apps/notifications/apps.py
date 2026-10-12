"""App registration for the ``notifications`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Push dispatch, dedupe, delivery tracking (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
