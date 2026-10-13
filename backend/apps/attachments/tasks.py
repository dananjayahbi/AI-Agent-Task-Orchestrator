"""Celery task registration shim for the attachments app.

Celery's ``autodiscover_tasks`` (``config/celery.py``) imports
``tasks.py`` in every installed app; the attachment-pipeline task itself
lives in :mod:`apps.attachments.pipeline` next to its stages and retry
seam (its MT target path — MT-1.12-01/07). Importing it here binds the
``attachments.process_attachment`` name to the worker's app. Keeping the
module a pure re-export preserves the ``leases.tasks`` thin-wrapper
convention without splitting pipeline logic across files.
"""

from __future__ import annotations

from .pipeline import process_attachment_task

__all__ = ["process_attachment_task"]
