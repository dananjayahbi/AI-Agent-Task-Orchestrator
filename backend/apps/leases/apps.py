"""App registration for the ``leases`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class LeasesConfig(AppConfig):
    """Claim, extend, release, sweep, fencing (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.leases"
