"""App registration for the ``merge`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class MergeConfig(AppConfig):
    """Merge queue API consumed by the Merge Executor (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.merge"
