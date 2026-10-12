"""App registration for the ``agents`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class AgentsConfig(AppConfig):
    """Agent sessions, capability registry (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.agents"
