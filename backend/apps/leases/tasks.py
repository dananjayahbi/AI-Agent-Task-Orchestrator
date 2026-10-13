"""Celery task entry points for the Section 9.9 background jobs (WP-1.7).

Thin wrappers: all logic lives in the service modules (``sweeper``,
``notifier``) so unit tests exercise the services directly and the worker
only provides scheduling, failure reporting and the next beat retry. Task
names are the canonical ones registered on the 60-second beat schedule in
``config/celery.py``.
"""

from __future__ import annotations

from celery import shared_task

from .notifier import notify_lease_expiring
from .sweeper import sweep_expired_leases


# Celery ships no type hints (pyproject's mypy override ignores its imports);
# the decorators are therefore Any — the service functions they wrap are
# fully typed, which is where the correctness lives.
@shared_task(name="leases.sweep_expired_leases")  # type: ignore[untyped-decorator]
def sweep_expired_leases_task() -> dict[str, int]:
    """Section 9.9 "Lease sweeper" — every 60 s (FR-LEA-04, FR-LEA-05)."""
    report = sweep_expired_leases()
    return {
        "reclaimed": report.reclaimed,
        "escalated": report.escalated,
        "audit_released": report.audit_released,
        "skipped": report.skipped,
    }


@shared_task(name="leases.notify_lease_expiring")  # type: ignore[untyped-decorator]
def notify_lease_expiring_task() -> dict[str, int]:
    """Section 9.9 "Lease-expiring notifier" — every 60 s (MT-1.7-04)."""
    report = notify_lease_expiring()
    return {
        "warned": report.warned,
        "already_warned": report.already_warned,
        "skipped": report.skipped,
    }
