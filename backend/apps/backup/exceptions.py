"""Backup failure type (MT-6.2-01; Section 20.4 item 1 — no silent no-ops).

Every backup half raises this on failure so the Celery task ends in the
worker's ``FAILURE`` state — a failed or skipped backup can never look
like a success (it feeds WP-6.4's alerting).
"""

from __future__ import annotations


class BackupError(RuntimeError):
    """A backup step (dump, sync, prune) failed; the job must surface it."""
