"""App registration for the core module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Settings-level wiring: error envelope, pagination, health (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
