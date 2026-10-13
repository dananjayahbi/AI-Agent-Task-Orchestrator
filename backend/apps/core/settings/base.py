"""Shared settings for every environment (parent plan Sections 9.10, 16.2).

Environment-specific modules (``dev.py``, ``prod.py``) import everything from
here and only adjust validation strictness and defaults. Every setting is read
from its canonical ``ORCHESTRATOR_*`` name (docs/plan/conventions/
configuration.md) and carries a documented default (Section 9.10).
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

from .env import get_bool, get_int, get_list, get_str

# backend/ directory (settings/ -> core/ -> apps/ -> backend/).
BASE_DIR = Path(__file__).resolve().parents[3]

# --- Section 9.10 group: secret keys ----------------------------------------
# Empty by default: dev.py substitutes an ephemeral key for local runs and
# prod.py refuses to boot without a strong value (Section 16.2). Never commit
# a real value (plan 20.4 item 3).
SECRET_KEY = get_str("ORCHESTRATOR_SECRET_KEY", "")

# --- Runtime debug posture (compose dev/prod split, MT-0.2-02) --------------
# Template default is false; dev.py re-reads with a dev-friendly default.
DEBUG = get_bool("ORCHESTRATOR_DEBUG", False)

# --- Section 9.10 group: database and cache URLs ----------------------------
# Compose always supplies ORCHESTRATOR_DATABASE_URL (derived from the
# ORCHESTRATOR_DATABASE_* components — single source for credentials). The
# fallback below exists for bare host runs only and uses the documented
# component defaults from configuration.md.


def build_database_url() -> str:
    """Resolve the effective database URL from the canonical environment names."""
    url = get_str("ORCHESTRATOR_DATABASE_URL", "")
    if url:
        return url
    user = quote(get_str("ORCHESTRATOR_DATABASE_USER", "orchestrator"), safe="")
    password = quote(get_str("ORCHESTRATOR_DATABASE_PASSWORD", "change-me"), safe="")
    name = get_str("ORCHESTRATOR_DATABASE_NAME", "orchestrator")
    return f"postgresql://{user}:{password}@localhost:5432/{name}"


DATABASE_URL = build_database_url()

_parsed_database_url = urlparse(DATABASE_URL)
if _parsed_database_url.scheme not in ("postgres", "postgresql"):
    # Fail fast at startup with a clear message (Section 9.10); the CI service
    # containers use postgres:// while Compose derives postgresql://.
    raise ImproperlyConfigured(
        "ORCHESTRATOR_DATABASE_URL must use the postgresql:// scheme "
        f"(got scheme {_parsed_database_url.scheme!r})."
    )

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _parsed_database_url.path.lstrip("/"),
        "USER": unquote(_parsed_database_url.username or ""),
        "PASSWORD": unquote(_parsed_database_url.password or ""),
        "HOST": _parsed_database_url.hostname or "",
        "PORT": str(_parsed_database_url.port or 5432),
    }
}

# Cache / pub-sub (Section 9.10). The compose stack points this at Redis on the
# internal network; bare host runs default to the documented local endpoint.
_CACHE_URL = get_str("ORCHESTRATOR_CACHE_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": _CACHE_URL,
    }
}

# Event publish channel (Section 9.6 post-commit fan-out; MT-1.9-03) —
# Section 9.10 group `EVENTS_`, documented defaults per configuration.md:
# the channel name is a fixed default; the publish URL falls back to the
# cache Redis so the Compose stack needs no additional wiring, and can be
# pointed elsewhere only through its canonical env name.
EVENTS_CHANNEL = get_str("ORCHESTRATOR_EVENTS_CHANNEL", "orchestrator:events")
EVENTS_REDIS_URL = get_str("ORCHESTRATOR_EVENTS_REDIS_URL", _CACHE_URL)
# SSE heartbeat cadence (Section 9.6: "Heartbeat comments every 15 s keep
# Cloudflare and mobile connections alive"; MT-1.10-04). The default is the
# plan's 15 s; the interval is configurable for tests and for downward
# review only — raising it toward proxy idle timeouts (Cloudflare ~100 s
# class) re-opens RISK-05 and belongs to WP-5.1's verification, not an
# ops tweak (configuration.md row).
EVENTS_HEARTBEAT_SECONDS = get_int("ORCHESTRATOR_EVENTS_HEARTBEAT_SECONDS", 15)

# --- Section 9.10 group: Celery broker (WP-1.7; ADR-003) --------------------
# Worker/beat (Section 16.1 services, Section 9.9 jobs) take broker and result
# backend from the documented `CACHE_` name in configuration.md. The URL falls
# back to the cache Redis so the Compose stack needs no additional wiring
# (same pattern as EVENTS_REDIS_URL above); the scheme is validated at
# startup (Section 16.2 fail-fast posture — configuration.md already pins
# redis://; rediss:// is accepted as the same family over TLS).
CELERY_BROKER_URL = get_str("ORCHESTRATOR_CACHE_BROKER_URL", _CACHE_URL)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
_parsed_broker_url = urlparse(CELERY_BROKER_URL)
if _parsed_broker_url.scheme not in ("redis", "rediss"):
    raise ImproperlyConfigured(
        "ORCHESTRATOR_CACHE_BROKER_URL must use the redis:// scheme "
        f"(got scheme {_parsed_broker_url.scheme!r})."
    )
# Server-side clock is UTC everywhere (P7): workers and beat compute job
# schedules and lease timestamps against the same clock the API uses.
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

# --- Section 9.10 group: allowed hosts and CORS/CSRF origins ----------------
# Dev/test fallback includes loopback plus `testserver` so a fresh clone and
# the unit suite boot with no environment (Section 9.10 documented defaults).
# prod.py requires an explicit, non-placeholder value (Section 16.2).
ALLOWED_HOSTS = get_list(
    "ORCHESTRATOR_ALLOWED_HOSTS",
    ["localhost", "127.0.0.1", "[::1]", "testserver"],
)
CSRF_TRUSTED_ORIGINS = get_list("ORCHESTRATOR_CSRF_ORIGINS", ["http://localhost:3000"])
# Read now (Section 9.10 group); wired into CORS middleware with the web client
# (WP-4.1) — the mobile client authenticates with tokens and sends no cookies.
CORS_ALLOWED_ORIGINS = get_list("ORCHESTRATOR_CORS_ORIGINS", ["http://localhost:3000"])

# --- Section 9.10 group: storage backend (Section 16.3) ---------------------
STORAGE_BACKEND = get_str("ORCHESTRATOR_STORAGE_BACKEND", "local")
MEDIA_ROOT = get_str("ORCHESTRATOR_STORAGE_MEDIA_ROOT", "/media")
# Reserved for the S3-compatible backend (validated when storage=s3 activates,
# WP-6.2); read here so the whole group resolves from one module (Section 9.10).
STORAGE_S3_ENDPOINT = get_str("ORCHESTRATOR_STORAGE_S3_ENDPOINT", "")
STORAGE_S3_BUCKET = get_str("ORCHESTRATOR_STORAGE_S3_BUCKET", "")
STORAGE_S3_ACCESS_KEY_ID = get_str("ORCHESTRATOR_STORAGE_S3_ACCESS_KEY_ID", "")
STORAGE_S3_SECRET_ACCESS_KEY = get_str("ORCHESTRATOR_STORAGE_S3_SECRET_ACCESS_KEY", "")

# --- Section 9.10 group: attachment limits (Section 9.5) ---------------------
# The Section 9.5 defaults, environment-overridable; unit suffixes live in
# the environment names (configuration.md rule 4). Byte values, not MB —
# configuration.md's units rule: a size setting always says _BYTES.
ATTACHMENT_MAX_FILE_BYTES = get_int("ORCHESTRATOR_ATTACHMENT_MAX_FILE_BYTES", 25 * 1024 * 1024)
ATTACHMENT_MAX_PER_TASK = get_int("ORCHESTRATOR_ATTACHMENT_MAX_PER_TASK", 10)
ATTACHMENT_MAX_TOTAL_BYTES = get_int("ORCHESTRATOR_ATTACHMENT_MAX_TOTAL_BYTES", 100 * 1024 * 1024)
# Section 12.4 / OQ-10's default retention grace period (days after the
# task is archived before the retention job purges attachments). The
# documented default, never re-decided here (MT-1.11-05 out of scope).
ATTACHMENT_RETENTION_GRACE_DAYS = get_int("ORCHESTRATOR_ATTACHMENT_RETENTION_GRACE_DAYS", 30)

# --- Section 9.10 group: OCR engine (Sections 6.6, 9.10; WP-1.12) ------------
# Tesseract-based default behind the pluggable interface (Section 6.6:
# "Local and free; replaceable by vision-model OCR"). An unknown engine
# name fails fast at the point of use, not silently OCR-less.
OCR_ENGINE = get_str("ORCHESTRATOR_OCR_ENGINE", "tesseract")
# The tesseract executable (name on PATH or absolute path); the worker
# image provisions the binary (Section 6.6 default engine).
OCR_TESSERACT_CMD = get_str("ORCHESTRATOR_OCR_TESSERACT_CMD", "tesseract")

# --- Section 9.10 group: description provider (Section 9.5; OQ-07) -----------
# Section 22's recorded default: disabled — vision/layout captions arrive
# with WP-1.13; the pipeline must complete OCR-only without them (9.5).
DESCRIPTION_PROVIDER = get_str("ORCHESTRATOR_DESCRIPTION_PROVIDER", "disabled")

# --- Section 9.10 group: attachment pipeline (Section 9.5 stages; WP-1.12) ---
# Documented defaults chosen by WP-1.12 (plan 20.4 item 3 — the plan fixes
# "configurable", not the values; each is recorded in the WP changelog and
# configuration.md). Unit suffixes follow configuration.md's units rule.
ATTACHMENT_IMAGE_MAX_EDGE_PX = get_int("ORCHESTRATOR_ATTACHMENT_IMAGE_MAX_EDGE_PX", 2048)
ATTACHMENT_CHUNK_MAX_TOKENS = get_int("ORCHESTRATOR_ATTACHMENT_CHUNK_MAX_TOKENS", 512)
ATTACHMENT_TOKEN_ESTIMATOR = get_str("ORCHESTRATOR_ATTACHMENT_TOKEN_ESTIMATOR", "chars_div_4")
ATTACHMENT_SUMMARY_PROVIDER = get_str("ORCHESTRATOR_ATTACHMENT_SUMMARY_PROVIDER", "disabled")
ATTACHMENT_SUMMARY_BUDGET_TOKENS = get_int("ORCHESTRATOR_ATTACHMENT_SUMMARY_BUDGET_TOKENS", 512)
ATTACHMENT_SUMMARY_MAX_TOKENS = get_int("ORCHESTRATOR_ATTACHMENT_SUMMARY_MAX_TOKENS", 120)
ATTACHMENT_RETRY_MAX_ATTEMPTS = get_int("ORCHESTRATOR_ATTACHMENT_RETRY_MAX_ATTEMPTS", 3)
ATTACHMENT_RETRY_BACKOFF_SECONDS = get_int("ORCHESTRATOR_ATTACHMENT_RETRY_BACKOFF_SECONDS", 60)
ATTACHMENT_PARSE_TIMEOUT_SECONDS = get_int("ORCHESTRATOR_ATTACHMENT_PARSE_TIMEOUT_SECONDS", 60)

# --- Section 9.10 group: request body sizing (Section 9.7; WP-3.2) ----------
# Django's DATA_UPLOAD_MAX_MEMORY_SIZE raised from its 2.5 MB default so
# the Section 9.7 degraded path is reachable: the submission endpoint
# must *accept* an oversize patch (5 MB cap +1 and beyond) to store
# "stats and file list only" — the default would answer 500 before the
# view ran. 32 MiB is WP-3.2's recorded reading (a bound still guards
# memory; beyond it the view answers VALIDATION_ERROR, never a silent
# accept), flagged for owner confirmation (Section 20.1 item 5) in
# configuration.md. Byte value; `_BYTES` unit suffix per that document.
DATA_UPLOAD_MAX_MEMORY_SIZE = get_int("ORCHESTRATOR_REQUEST_BODY_MAX_BYTES", 32 * 1024 * 1024)

# --- Section 9.10 group: feature flags --------------------------------------
# Default: none enabled (configuration.md). Flag semantics arrive with each
# consumer; this list is the resolved, documented value.
FEATURE_FLAGS = get_list("ORCHESTRATOR_FEATURE_FLAGS", [])

# --- Section 9.10 group: token lifetimes ------------------------------------
# Documented defaults fixed by WP-1.2 (configuration.md per-setting rows);
# unit suffix lives in the environment name. Lifetime values are read here so
# every consumer (authentication, issuance, refresh) computes expiry from one
# place — Section 9.10's "documented default" rule.
TOKEN_LIFETIME_OWNER_SESSION_HOURS = get_int("ORCHESTRATOR_TOKEN_LIFETIME_OWNER_SESSION_HOURS", 12)
# Agent bearer tokens are "long-lived but revocable" (Section 12.2): 30 days
# by default — long enough for the host's user-level config (Section 10.3
# step 3), short enough that rotation is routine. Flagged for owner
# confirmation in configuration.md (MT-1.2-03).
TOKEN_LIFETIME_AGENT_HOURS = get_int("ORCHESTRATOR_TOKEN_LIFETIME_AGENT_HOURS", 720)
# Device-bound tokens (Section 12.2 mobile, ADR-006): 90 days by default —
# the phone re-registers on rotation, and remote revocation (lost phone) is
# the real control, not expiry. Unit is days per the Section 9.10 group's
# `TOKEN_LIFETIME_DEVICE_DAYS` name; flagged for owner confirmation (MT-1.2-04).
TOKEN_LIFETIME_DEVICE_DAYS = get_int("ORCHESTRATOR_TOKEN_LIFETIME_DEVICE_DAYS", 90)

# --- Section 9.10 group: rate limits ---------------------------------------
# FR-SEC-05 (MT-1.2-06): API-side budgets for the Section 9.2 agent- and
# device-facing endpoints only — throttling the owner's web endpoints would
# silently widen FR-SEC-05's scope, so those stay unthrottled here (the edge
# half of Section 12.3's layered rate limits arrives with WP-3.x).
# Defaults chosen for the Section 18 performance scenario (20 agents,
# checkpoints every 30 s = 2/min per token) with headroom for claim/release/
# work-poll bursts; budgets are keyed per token, so the 20 agents never share
# one. Unit suffix lives in the environment name (configuration.md rule 4).
# Both defaults are flagged for owner confirmation (Section 20.1 item 5).
RATE_LIMIT_AGENT_PER_MINUTE = get_int("ORCHESTRATOR_RATE_LIMIT_AGENT_PER_MINUTE", 120)
RATE_LIMIT_DEVICE_PER_MINUTE = get_int("ORCHESTRATOR_RATE_LIMIT_DEVICE_PER_MINUTE", 60)

# --- Manifest binding (Section 10.3; NFR-06; MT-1.3-05) ---------------------
# `orchestrator_api` in every generated orchestrator.json comes from this
# setting, never from code or request input (NFR-06: env-only; MT-1.3-05
# risk note). Group `API_` was added by MT-1.3-05 because Section 9.10 does
# not enumerate an API-base group while Section 10.3 requires the value —
# the new group is recorded in configuration.md and flagged for owner
# confirmation (Section 20.1 item 5). Documented default: the Compose
# backend's published address with the Section 9.2 base path (the Section
# 10.3 example's shape); tunnel deployments (Section 15) override it.
ORCHESTRATOR_API_BASE_URL = get_str("ORCHESTRATOR_API_BASE_URL", "http://localhost:8000/api/v1")
if ORCHESTRATOR_API_BASE_URL.split(":", 1)[0] not in ("http", "https"):
    # Fail fast at startup with a clear message (Section 9.10) — a manifest
    # pointing at a non-URL would break bridge binding (Section 10.3 step 2).
    raise ImproperlyConfigured(
        "ORCHESTRATOR_API_BASE_URL must be an absolute http(s) URL "
        f"(got scheme {ORCHESTRATOR_API_BASE_URL.split(':', 1)[0]!r})."
    )

# --- Project identity -------------------------------------------------------
ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True  # Principle P7: server-clock UTC everywhere (Section 0.4)
TIME_ZONE = "UTC"

# --- Section 7.1: the user entity -------------------------------------------
# The accounts app owns the User model (Section 9.1); set before the first
# migration exists so auth and contenttypes bind to it from the start.
AUTH_USER_MODEL = "accounts.User"

# --- Section 12.2: owner session storage ------------------------------------
# Signed-cookie sessions: the session itself lives in the secure, HTTP-only
# cookie (Section 12.2) and the server stores NO plaintext session credential —
# revocation and expiry are enforced by the hashed `owner_session` API Token
# row checked on every authenticated request (FR-SEC-02; MT-1.2-01 changelog
# records this storage mechanic per the MT risk note).
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
# The cookie lives exactly as long as the owner_session token row by default;
# `login()` also pins the per-session expiry to the same Section 9.10 lifetime.
SESSION_COOKIE_AGE = TOKEN_LIFETIME_OWNER_SESSION_HOURS * 3600
# Section 12.2: session cookie is HTTP-only (the csrftoken cookie is not — the
# web client must read it to echo it back; it carries no authority alone).
SESSION_COOKIE_HTTPONLY = True

# --- Templates --------------------------------------------------------------
# APP_DIRS picks up app templates (Swagger UI from drf_spectacular — the first
# real template consumer; MT-1.1-04 found TEMPLATES was never configured by
# MT-1.1-01 because nothing rendered templates until now). The request context
# processor is required by the DRF browsable API and spectacular's UI views.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ],
        },
    },
]

# --- Installed applications (Section 9.1 module layout) ---------------------
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "drf_spectacular",  # ADR-005 — OpenAPI generation (MT-1.1-04)
    "apps.accounts",
    "apps.agents",
    "apps.attachments",
    "apps.audit",
    "apps.core",
    "apps.events",
    "apps.leases",
    "apps.merge",
    "apps.notifications",
    "apps.projects",
    "apps.tasks",
]

# --- Structured logging (Section 17; MT-1.1-02) -----------------------------
# Level comes from the canonical ORCHESTRATOR_LOG_LEVEL (configuration.md
# group `LOG_`); documented defaults: INFO here, DEBUG in dev.py.
LOG_LEVEL = get_str("ORCHESTRATOR_LOG_LEVEL", "INFO")

# One JSON formatter on the root handler; every logger (django.*, apps.*)
# propagates to root, so all service logging shares one shape and one
# scrubbing pass. Request lines come from apps.core.middleware; Uvicorn's own
# access log is disabled in the documented run command so no plain-text line
# can bypass this pipeline (Section 17).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "apps.core.logging.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {"django": {"level": LOG_LEVEL}},
}

# --- API defaults (ADR-005; envelope per Section 9.2) -----------------------
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.exceptions.orchestrator_exception_handler",
    # ADR-005: DRF with generated OpenAPI — the schema generator is
    # drf-spectacular (pinned; choice recorded in the WP-1.1 changelog).
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Section 12.2: credentials resolve through the explicit authorization
    # header first (MT-1.2-03: agent/device tokens and the Section 15.4
    # token-auth transport of an owner session token), then the signed-cookie
    # session bound to a revocable `owner_session` API Token row (MT-1.2-01).
    # An unauthenticated request falls through both to DRF's NotAuthenticated
    # -> AUTH_REQUIRED envelope.
    # Views that must stay unauthenticated (health, schema, login) opt out
    # explicitly with `authentication_classes = []`.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.TokenBearerAuthentication",
        "apps.accounts.authentication.OwnerSessionAuthentication",
    ],
    # FR-SEC-05 (MT-1.2-06): scope -> rate for apps.core.throttling. The
    # scopes are the Section 9.10 RATE_LIMIT_ group above — every threshold
    # traces to a documented, environment-configurable default (no magic
    # numbers in the throttle classes).
    "DEFAULT_THROTTLE_RATES": {
        "agent": f"{RATE_LIMIT_AGENT_PER_MINUTE}/min",
        "device": f"{RATE_LIMIT_DEVICE_PER_MINUTE}/min",
    },
}

# --- OpenAPI document (ADR-005; NFR-11; MT-1.1-04) --------------------------
# The generated document is the client contract: served at /api/v1/schema
# (serving path decided once in MT-1.1-04 and recorded in the WP changelog),
# snapshotted under schemas/, drift-gated in CI. Health/Ops routes are
# root-level by Section 16.1 and documented alongside the /api/v1 surface.
SPECTACULAR_SETTINGS = {
    "TITLE": "AI Agent Task Orchestrator",
    "DESCRIPTION": (
        "REST API contract for the AI Agent Task Orchestrator. NFR-11: this "
        "document is the single source of truth for web and mobile clients. "
        "Errors use the Section 9.2 envelope; list endpoints are cursor-"
        "paginated (docs/plan/conventions/pagination.md)."
    ),
    "VERSION": "1.0.0",
    # The contract itself is public (Section 9.2); individual resource
    # endpoints still enforce their own auth when WPs add it.
    "SERVE_AUTHENTICATION": [],
    "SERVE_PERMISSIONS": [],
}

# --- Middleware --------------------------------------------------------------
# Order is load-bearing: CorrelationIdMiddleware installs the request scope
# first, RequestLoggingMiddleware emits the per-request line inside it; health
# (MT-1.1-03) and the schema route (MT-1.1-04) follow.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.CorrelationIdMiddleware",
    "apps.core.middleware.RequestLoggingMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
