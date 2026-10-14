"""Celery application for the orchestrator's background jobs (Section 9.9).

Loaded eagerly from ``config/__init__.py`` so a worker started as
``celery -A config.celery`` (Compose worker/beat services, WP-1.7) finds the
app and its registered tasks. Django settings are read lazily through
``django.conf`` — the settings module comes from the standard
``DJANGO_SETTINGS_MODULE`` environment variable (the image sets
``apps.core.settings.prod``; the dev Compose override sets ``dev``), and the
Celery settings themselves are the ``CELERY_*`` names defined in
``apps.core.settings.base``.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

app = Celery("orchestrator")
app.config_from_object("django.conf:settings", namespace="CELERY")
# Discover ``tasks.py`` modules in every installed app (leases sweeper/notifier
# tasks arrive in MT-1.7-02 and MT-1.7-04).
app.autodiscover_tasks()

# Section 9.9 background jobs: both jobs run every 60 s on the beat schedule.
# The intervals are fixed by the plan (not env-tunable); task names are the
# canonical ones registered in ``apps.leases.tasks``.
app.conf.beat_schedule = {
    "lease-sweeper": {
        "task": "leases.sweep_expired_leases",
        "schedule": 60.0,
    },
    "lease-expiring-notifier": {
        "task": "leases.notify_lease_expiring",
        "schedule": 60.0,
    },
}


@app.on_after_finalize.connect  # type: ignore[untyped-decorator]
def register_backup_schedule(sender: Celery, **kwargs: object) -> None:
    """Add the Section 9.9 daily "Backup trigger" (WP-6.2; MT-6.2-03).

    Registered on finalize rather than at module import because the trigger
    time is configuration (``ORCHESTRATOR_BACKUP_TRIGGER_HOUR``/``_MINUTE``,
    read through ``apps.core.settings.base``): this module is imported from
    ``config/__init__.py`` before ``DJANGO_SETTINGS_MODULE`` is guaranteed to
    resolve on every host path (Section 9.10 lazy-settings discipline). Both
    the worker and beat processes finalize the app before consuming the
    schedule, so the entry is always present where it matters. The task name
    is the canonical one registered in ``apps.backup.tasks``.
    """
    from django.conf import settings

    sender.conf.beat_schedule["backup-trigger"] = {
        "task": "backup.run_daily_backup",
        "schedule": crontab(
            hour=settings.BACKUP_TRIGGER_HOUR,
            minute=settings.BACKUP_TRIGGER_MINUTE,
        ),
    }
