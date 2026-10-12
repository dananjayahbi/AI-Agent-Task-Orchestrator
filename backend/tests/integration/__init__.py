"""Integration suite — Section 18's "API with database and Redis" layer.

These tests run **only** against real Postgres: the CI ``integration-tests``
job provisions the service containers and runs them with
``--ds apps.core.settings.dev`` (the module that binds ``DATABASES`` to
``ORCHESTRATOR_DATABASE_URL`` and ``CACHES`` to ``ORCHESTRATOR_CACHE_URL``).
Under the hermetic SQLite unit settings every module here skips itself with
that command in the skip reason, so the unit job stays service-free while
the layer boundary stays explicit (no silent wrong-backend runs).
"""

from __future__ import annotations
