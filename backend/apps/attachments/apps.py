"""App registration for the ``attachments`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class AttachmentsConfig(AppConfig):
    """Upload API, storage abstraction, pipeline jobs, retrieval formats (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.attachments"
