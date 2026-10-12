"""Startup-binding errors for the bridge (parent plan Section 10.3 steps 1–3; WP-2.2).

One boundary exception family for the manifest/token binding that runs before the
MCP server starts, plus the Section 10.11 API-version gate the client runs at
startup. The entry point catches :class:`BindingError`, logs it through the
structured logger (MT-2.1-03 — correlation id included), prints one scrubbed
line to stderr and exits non-zero — no traceback, no secret. These are local
startup failures, not API responses, so Section 9.2's canonical error catalog
does not apply to them (MT-2.2-02 scope).

Distinguishable classes drive the user's fix (MT-2.2-02 acceptance — "malformed
file" vs "unsupported version" vs "no token"):

* :class:`ManifestNotFoundError` — no manifest up to the Git root; create one.
* :class:`ManifestParseError` — the file is unreadable or not valid JSON/UTF-8;
  fix the file.
* :class:`ManifestValidationError` — the document does not match the published
  schema ``schemas/manifest.v1.json``; fix the file.
* :class:`ManifestVersionError` — the file parses but declares a
  ``schema_version`` this bridge does not support; upgrade the bridge (or
  regenerate an ancient manifest).
* :class:`TokenError` — no usable token in the two legitimate sources; configure
  it (env var or ``orchestrator init``).
* :class:`ApiVersionError` — the backend advertises an incompatible API version
  header (Section 10.11); upgrade the bridge or the backend.

Message constants live here once so a rename never scatters (MT-2.2-01 risk
note).
"""

from __future__ import annotations

__all__ = [
    "INIT_COMMAND",
    "ApiVersionError",
    "BindingError",
    "ManifestNotFoundError",
    "ManifestParseError",
    "ManifestValidationError",
    "ManifestVersionError",
    "TokenError",
]

#: The Section 10.11 / FR-MCP-08 init command — one spelling, one place.
INIT_COMMAND = "orchestrator init"


class BindingError(Exception):
    """Startup binding failed; ``str(exc)`` is user-facing, clear and secret-free."""


class ManifestNotFoundError(BindingError):
    """No manifest between the cwd and the Git root (Section 10.3 step 1)."""


class ManifestParseError(BindingError):
    """The manifest file is unreadable or not valid JSON/UTF-8 ("fix the file")."""


class ManifestValidationError(BindingError):
    """The manifest does not match the published schema ("fix the file")."""


class ManifestVersionError(BindingError):
    """Unsupported ``schema_version`` ("upgrade the bridge" — distinct message)."""


class TokenError(BindingError):
    """No usable agent token in the environment or user-level config (step 3)."""


class ApiVersionError(BindingError):
    """Backend API version incompatible with this bridge (Section 10.11).

    Raised by :func:`orchestrator_bridge.transport.verify_api_version` when the
    backend's advertised version-header value parses but does not match the
    version this bridge speaks; a backend that does not advertise the header at
    all is *not* a mismatch (unverified — see the transport module), so this
    error always means "upgrade the bridge or the backend".
    """
