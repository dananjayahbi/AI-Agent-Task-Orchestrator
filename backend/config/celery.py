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
