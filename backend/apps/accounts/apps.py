"""App registration for the ``accounts`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Users, token issuance and validation, device registration, permissions (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
