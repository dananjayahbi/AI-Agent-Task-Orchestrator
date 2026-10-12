"""ASGI entrypoint — Uvicorn/Daphne per parent plan Section 6.6.

Uvicorn imports ``config.asgi:application`` with the working directory at
``backend/`` (see the run command in CONTRIBUTING.md). The settings module
defaults to dev for host runs; the container image sets
``DJANGO_SETTINGS_MODULE=apps.core.settings.prod`` (Section 16.2).
"""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.core.settings.dev")

application = get_asgi_application()
