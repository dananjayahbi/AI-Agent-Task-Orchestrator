"""Backup app: the Section 9.9 daily backup trigger (WP-6.2, NFR-05).

Database dump, media sync and backup retention live here — beat schedules
the trigger (``config/celery.py``), the worker executes it against the
media volume and the second-location backup mount (``infra/compose``).
No models: backups are filesystem artifacts, not rows.
"""
