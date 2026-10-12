"""Test settings — hermetic unit-suite environment (parent plan Section 18).

The unit layer must run in CI's ``unit-tests`` job with **no services**: the
suite exercises real models, sessions and API routes, so it needs a real
relational store and a real cache, but neither Postgres nor Redis (Section 18
reserves "API with database and Redis" for the *integration* layer —
``backend/tests/integration/``, where the CI job provisions them).

Choices and their limits, recorded here so nobody mistakes this for the
production topology:

* **SQLite in-memory** — supports everything WP-1.2 exercises (FKs, check
  constraints, JSON columns, transactions). Postgres-specific behaviour
  (``SKIP LOCKED`` claim races, advisory locks) is out of this layer's scope
  by Section 18's own split and joins with WP-1.6's concurrency tests.
* **LocMem cache** — the DRF throttles (MT-1.2-06) and any cache-touching
  request run against an isolated per-process cache; no Redis needed, no
  cross-test bleed (each test run gets a fresh process-level cache, and tests
  clear it explicitly).

Everything else — secret posture, cookie flags, error envelope — stays exactly
as ``dev.py`` defines it so the unit layer tests the same contract the
container serves.
"""

from __future__ import annotations

from .dev import *  # noqa: F403

# Real relational semantics without a service (Section 18 unit layer).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Real cache API without a service; isolated per test process.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
