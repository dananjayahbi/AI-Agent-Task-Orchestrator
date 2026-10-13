"""App registration for the ``attachments`` module (parent plan Section 9.1).

``ready()`` completes the MT-1.11-03 enqueue seam (MT-1.12-01): the
upload path's ``enqueue_processing`` hook is wired to the real Celery
job (Section 9.9 "on upload") in every process that talks to a broker —
dev server, prod web, worker. The hermetic unit layer
(``apps.core.settings.test``, Section 18) keeps the documented no-op
default because it runs with no broker; tests that exercise the seam
install their own (``set_enqueue_seam``), so no suite silently depends
on Redis.
"""

from __future__ import annotations

from django.apps import AppConfig


class AttachmentsConfig(AppConfig):
    """Upload API, storage abstraction, pipeline jobs, retrieval formats (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.attachments"

    def ready(self) -> None:
        """Wire the pipeline enqueue seam (MT-1.12-01; MT-1.11-03's hook)."""
        from .pipeline import install_pipeline_enqueue_seam

        install_pipeline_enqueue_seam()
