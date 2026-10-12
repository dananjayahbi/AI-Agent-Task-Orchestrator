"""Development settings — the default for host runs (manage.py, Uvicorn, tests).

Bootable from a fresh clone with no environment and no committed secrets
(plan 20.4 item 3): placeholders and documented defaults are tolerated, debug
is on unless explicitly disabled, and the database/cache endpoints fall back to
their documented local values. The compose dev overlay selects this module for
the containerized dev stack as well.
"""

from __future__ import annotations

from django.core.management.utils import get_random_secret_key

from .base import *  # noqa: F403
from .base import SECRET_KEY as _BASE_SECRET_KEY
from .env import get_bool, get_str

# Dev default: debug on unless the environment explicitly says otherwise
# (the compose dev overlay sets ORCHESTRATOR_DEBUG=true; the template default
# stays false for the prod render).
DEBUG = get_bool("ORCHESTRATOR_DEBUG", True)

# Dev default: verbose structured logs unless the environment overrides it
# (the shared base default is INFO — documented in configuration.md's row).
LOG_LEVEL = get_str("ORCHESTRATOR_LOG_LEVEL", "DEBUG")

# No secrets are committed: an unset key is replaced with an ephemeral one
# regenerated on every start — sessions signed with it simply do not survive a
# restart, which is exactly the local-development trade-off (Section 16.2).
SECRET_KEY = _BASE_SECRET_KEY or get_random_secret_key()
