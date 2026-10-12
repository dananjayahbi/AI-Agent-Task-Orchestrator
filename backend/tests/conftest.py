"""Shared pytest bootstrap: configure the test settings module, then Django.

Must run before any test module imports ``django.*`` (pytest imports this file
first). pytest-django (WP-1.2) already selects the same module from the
``DJANGO_SETTINGS_MODULE`` ini option and performs its own setup; the explicit
``setdefault`` + ``django.setup()`` below keep this file self-sufficient for
direct imports and are idempotent with the plugin's setup (Django's app
registry guards against double population).

The test module (``apps.core.settings.test``) is the hermetic unit-layer
environment: SQLite in-memory + LocMem cache, everything else inherited from
``dev`` — see its docstring for the Section 18 layering rationale.
"""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.core.settings.test")

import django  # noqa: E402

django.setup()
