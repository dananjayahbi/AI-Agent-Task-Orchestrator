"""App registration for the ``audit`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Audit reports, Policy Engine, review decisions (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
