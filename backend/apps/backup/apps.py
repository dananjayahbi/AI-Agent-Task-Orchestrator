"""App registration for the ``backup`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class BackupConfig(AppConfig):
    """Daily database dump + media sync trigger, backup retention (Section 9.9)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.backup"
