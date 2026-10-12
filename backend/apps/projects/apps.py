"""App registration for the ``projects`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """Project registry, ids, policy, manifest generation (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
