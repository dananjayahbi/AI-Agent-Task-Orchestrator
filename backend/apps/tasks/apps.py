"""App registration for the ``tasks`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class TasksConfig(AppConfig):
    """Task CRUD, sequencing, transitions, checkpoints, resolutions (9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tasks"
