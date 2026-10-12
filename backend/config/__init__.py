"""Django project package for the AI Agent Task Orchestrator backend.

Exports the Celery app (WP-1.7, ADR-003) so ``celery -A config.celery`` and
``shared_task`` callers resolve the same application.
"""

from config.celery import app as celery_app

__all__ = ("celery_app",)
