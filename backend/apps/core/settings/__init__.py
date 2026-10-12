"""Django settings package — one module per environment (parent plan Section 9.10).

Selected through ``DJANGO_SETTINGS_MODULE`` (the framework's own selector, used
exactly once — no second configuration mechanism):

* ``apps.core.settings.dev``  — default for host runs (``manage.py``, Uvicorn,
  tests, CI); relaxes the Section 16.2 rules so a fresh clone boots with no
  secrets committed (plan 20.4 item 3).
* ``apps.core.settings.prod`` — default inside the container image; refuses to
  boot with weak or missing required values (Section 16.2).

Both import everything from ``base.py``. The split decision is recorded in
CONTRIBUTING.md and the WP-1.1 changelog.
"""
