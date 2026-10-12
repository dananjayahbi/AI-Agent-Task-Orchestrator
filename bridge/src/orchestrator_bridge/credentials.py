"""Agent token loading for session binding (parent plan Section 10.3 step 3; MT-2.2-03).

Sourcing is exactly the plan's sentence — *environment or user-level config,
never from the manifest* — resolved by MT-2.1-02's layered loader
(env > user file > defaults; FR-SEC-04: no repo-tracked file, no cwd, no argv).
:func:`require_agent_token` is the fail-fast gate that runs after manifest
validation and before any session work: it proves a token is configured and
plausibly shaped for an ``Authorization`` header, then hands back the value that
already lives in the ``Settings`` object — the token is never copied into module
globals or a second structure, so ``Settings`` plus the logging layer's scrubbing
remain the single redaction boundary.

Deliberately NOT done here (Section 12.2; FR-SEC-01): no signature, expiry or
revocation check, no decoding of any kind — PAT-style tokens are opaque bearer
values to the client; the *backend* verifies them when the session opens
(MT-2.2-04). Local checking is limited to header safety: non-empty (the loader
already collapses empty/whitespace-only values to ``None``) and free of
whitespace or control characters that would break or inject into the header line.

The message on failure names both legitimate sources — the env var and
``orchestrator init`` — and never echoes any token material (MT-2.2-03
acceptance; Section 17 no-secrets rule).
"""

from __future__ import annotations

from .config import Settings, _ENV_KEYS, default_user_config_path
from .errors import INIT_COMMAND, TokenError

__all__ = ["require_agent_token"]


def _header_safe(token: str) -> bool:
    """Plausible bearer value: no whitespace and no ASCII control characters."""
    return not any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in token)


def require_agent_token(settings: Settings) -> str:
    """Return the configured agent token or fail fast with a non-leaking message.

    Precedence (Section 10.3 step 3): ``ORCHESTRATOR_AGENT_TOKEN`` environment
    variable first, then the user-level config file written by
    ``orchestrator init`` — both already layered into ``settings.agent_token``.
    Raises :class:`TokenError` naming those two sources without revealing
    whether a partial/empty value was found.
    """
    token = settings.agent_token
    if token is None:
        raise TokenError(
            f"agent token not configured: set {_ENV_KEYS['agent_token']} "
            f"(environment) or run '{INIT_COMMAND}' to store one in the "
            f"user-level config ({default_user_config_path()})"
        )
    if not _header_safe(token):
        raise TokenError(
            f"agent token from {_ENV_KEYS['agent_token']} or the user config is "
            "not a valid bearer value (contains whitespace or control "
            f"characters); fix the value or re-run '{INIT_COMMAND}'"
        )
    return token
