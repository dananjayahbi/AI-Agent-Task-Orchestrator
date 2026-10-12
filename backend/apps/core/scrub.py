"""Token/secret scrubbing and log-size truncation (Sections 17, 12.4).

One implementation, used by every sink that can echo data: the JSON log
formatter and the error envelope (the MT-1.1-02 risk note requires that codes
such as ``VALIDATION_ERROR`` cannot leak a token through ``details``).
Over-redaction is deliberate (RISK-14): a redacted diagnostic value costs
nothing, a leaked credential costs a token rotation.

Truncation (Section 12.4: "logs … truncate attachment text"): every scrubbed
string is capped at :data:`MAX_SCRUBBED_CHARS` so attachment-derived text can
never bloat a log line or an error response.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

MAX_SCRUBBED_CHARS = 2000
_REDACTED = "[REDACTED]"
_TRUNCATION_SUFFIX = "…[truncated]"

# Order matters: bearer tokens carry their secret in the *second* token, so
# redact `Bearer <secret>` before the key/value pass would only eat "Bearer".
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+\S+")

# A secret-shaped *name* followed by `=` or `:` and then the value. The name
# matches liberally (SECRET_KEY=…, api-key: …, "password": "…") because this
# runs over free-form message text where the exact key is unknown.
_KEY_VALUE_PATTERN = re.compile(
    r"""(?ix)
    [A-Za-z0-9_.\-]*(
        authorization | password | passwd | secret | token |
        api[\-_]?key | apikey | credential | private[\-_]?key | access[\-_]?key
    )[A-Za-z0-9_.\-]*
    # An optional closing quote lets the pattern match a repr/JSON-formatted
    # key (`'password': …`, `"password": …`) — str(ValidationError) renders
    # exactly that, and an echoing message must not leak it (Sections 17,
    # 12.4; MT-1.1-02's envelope-scrubbing guarantee).
    (['\"]?\s*[=:]\s*)
    ("[^"]*"|'[^']*'|\S+)
    """
)

# Exact (or suffix-matched) names for structured fields: broad enough to catch
# credential-shaped keys, narrow enough to leave telemetry alone (a future
# `token_usage` / `input_tokens` field is data, not a credential).
_SECRET_EXTRA_KEY_NAMES = frozenset(
    {
        "authorization",
        "credential",
        "credentials",
        "key",
        "password",
        "passwd",
        "secret",
        "secret_key",
        "api_key",
        "apikey",
        "access_key",
        "private_key",
        "refresh_token",
        "access_token",
        "id_token",
        "token",
    }
)
_SECRET_EXTRA_KEY_SUFFIXES = (
    "_password",
    "_passwd",
    "_secret",
    "_token",
    "_credential",
    "_credentials",
)


def is_secret_extra_key(key: str) -> bool:
    """Whether a structured log/envelope field name denotes a credential."""
    lowered = key.lower()
    return lowered in _SECRET_EXTRA_KEY_NAMES or lowered.endswith(_SECRET_EXTRA_KEY_SUFFIXES)


def scrub_text(text: str) -> str:
    """Redact secret-shaped values in *text*, then cap its length."""
    result = _BEARER_PATTERN.sub(f"Bearer {_REDACTED}", text)
    result = _KEY_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{_REDACTED}", result
    )
    if len(result) > MAX_SCRUBBED_CHARS:
        result = result[:MAX_SCRUBBED_CHARS] + _TRUNCATION_SUFFIX
    return result


def scrub_value(key: str, value: object) -> object:
    """Scrub one structured value: redact by key first, then by content."""
    if is_secret_extra_key(key):
        return _REDACTED
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, Mapping):
        return {str(item_key): scrub_value(str(item_key), item) for item_key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [scrub_value(key, item) for item in value]
    return value


def scrub_mapping(mapping: Mapping[str, object]) -> dict[str, object]:
    """Scrub every entry of a structured payload (e.g. envelope ``details``)."""
    return {str(key): scrub_value(str(key), value) for key, value in mapping.items()}
