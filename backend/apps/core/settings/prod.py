"""Production settings — refuse to boot with weak or missing required values.

Startup validation per parent plan Sections 9.10 and 16.2: every required-in-prod
name from `docs/plan/conventions/configuration.md` must be present, non-weak and
non-placeholder; `ORCHESTRATOR_DEBUG` must be `false`. Violations raise
``ImproperlyConfigured`` at import time — before the server serves a single
request — listing every offending variable *by name only* (never by value, so
the error itself cannot leak a secret).

Weak means, concretely (documented so operators can self-diagnose):

* equal to a listed template placeholder (`change-me`, `changeme`, `secret`,
  `password`, `insecure` — the values shipped in `.env.example`);
* for `ORCHESTRATOR_SECRET_KEY`: shorter than 32 characters or starting with
  Django's `django-insecure-` development prefix;
* for the database password: shorter than 8 characters or empty.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

# The placeholder values shipped in infra/compose/.env.example — any of these
# is refused here (Section 16.2: "a default left unchanged from this file").
WEAK_PLACEHOLDER_VALUES = frozenset(
    {"change-me", "changeme", "secret", "password", "insecure"}  # pragma: allowlist secret
)

_MIN_SECRET_KEY_LENGTH = 32
_MIN_DATABASE_PASSWORD_LENGTH = 8
_WEAK_SECRET_KEY_PREFIX = "django-insecure-"  # pragma: allowlist secret
# Entries that never count as "real serving hostnames" in prod (Section 16.2).
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]", "::1", "testserver"})


def _required(name: str) -> str | None:
    """Return the raw environment value for *name*, or ``None`` when unset/empty."""
    value = os.environ.get(name, "").strip()
    return value or None


def _is_weak(value: str) -> bool:
    lowered = value.lower()
    return lowered in WEAK_PLACEHOLDER_VALUES or len(value) < _MIN_DATABASE_PASSWORD_LENGTH


def collect_prod_violations() -> list[str]:
    """Evaluate every Section 16.2 required-in-prod rule; return violations by name."""
    violations: list[str] = []

    if DEBUG:  # noqa: F405
        violations.append("ORCHESTRATOR_DEBUG must be 'false' in prod (Section 16.2)")

    secret_key = _required("ORCHESTRATOR_SECRET_KEY")
    if secret_key is None:
        violations.append("ORCHESTRATOR_SECRET_KEY is required in prod")
    elif (
        secret_key.lower() in WEAK_PLACEHOLDER_VALUES
        or len(secret_key) < _MIN_SECRET_KEY_LENGTH
        or secret_key.startswith(_WEAK_SECRET_KEY_PREFIX)
    ):
        violations.append(
            "ORCHESTRATOR_SECRET_KEY is weak: use a placeholder-free value of "
            f"at least {_MIN_SECRET_KEY_LENGTH} characters "
            '(generate with: python -c "import secrets; print(secrets.token_urlsafe(50))")'
        )

    allowed_hosts = _required("ORCHESTRATOR_ALLOWED_HOSTS")
    if allowed_hosts is None:
        violations.append("ORCHESTRATOR_ALLOWED_HOSTS is required in prod")
    elif allowed_hosts == "*":
        violations.append(
            "ORCHESTRATOR_ALLOWED_HOSTS is a wildcard; set the real serving "
            "hostnames (Section 16.2)"
        )
    else:
        # Loopback-only is the localhost placeholder in disguise: the API would
        # be unreachable from LAN/tunnel clients while still booting. Keep
        # loopback entries (the container's own health probe requests
        # 127.0.0.1) — but at least one real serving hostname must exist.
        hosts = [host.strip().lower() for host in allowed_hosts.split(",") if host.strip()]
        loopback_only = not hosts or all(host in _LOOPBACK_HOSTS for host in hosts)
        if loopback_only:
            violations.append(
                "ORCHESTRATOR_ALLOWED_HOSTS lists only loopback/test hosts; add "
                "the real serving hostnames (keep 127.0.0.1 for the container's "
                "own health probe) (Section 16.2)"
            )

    # The effective URL falls back to the ORCHESTRATOR_DATABASE_* components the
    # same way base.py resolves it, so a weak derived password is caught too.
    database_url = _required("ORCHESTRATOR_DATABASE_URL")
    if database_url is None:
        database_url = build_database_url()  # noqa: F405
    database_password = urlparse(database_url).password or ""
    if not database_password:
        violations.append("ORCHESTRATOR_DATABASE_PASSWORD (or DATABASE_URL) is required in prod")
    elif _is_weak(database_password):
        violations.append(
            "ORCHESTRATOR_DATABASE_PASSWORD is a weak placeholder or too short; "
            f"use at least {_MIN_DATABASE_PASSWORD_LENGTH} characters (Section 16.2)"
        )

    # S3 storage credentials are required exactly when the s3 backend is chosen
    # (configuration.md: "when s3"); the local volume needs none.
    if STORAGE_BACKEND == "s3":  # noqa: F405
        for name in ("ORCHESTRATOR_STORAGE_S3_ENDPOINT", "ORCHESTRATOR_STORAGE_S3_BUCKET"):
            if _required(name) is None:
                violations.append(f"{name} is required in prod when STORAGE_BACKEND=s3")
        for name in (
            "ORCHESTRATOR_STORAGE_S3_ACCESS_KEY_ID",
            "ORCHESTRATOR_STORAGE_S3_SECRET_ACCESS_KEY",
        ):
            value = _required(name)
            if value is None or value.lower() in WEAK_PLACEHOLDER_VALUES:
                violations.append(f"{name} is missing or weak in prod when STORAGE_BACKEND=s3")

    return violations


_violations = collect_prod_violations()
if _violations:
    raise ImproperlyConfigured(
        "Prod startup validation failed (parent plan Section 16.2): " + "; ".join(_violations)
    )

# --- Section 12.2 cookie posture (WP-1.2, MT-1.2-01) -------------------------
# Secure, HTTP-only session cookies: prod serves over TLS (Cloudflare edge,
# Section 15.1), so the sessionid and csrftoken cookies carry the Secure flag
# and can never be replayed over plaintext. The dev module keeps the flags off
# because the LAN address runs plain HTTP for development (Section 12.4
# documented risk); HTTP-only is unconditional in base.py for every
# environment.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
