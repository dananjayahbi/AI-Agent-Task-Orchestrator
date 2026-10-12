"""The single redaction point for bridge logs (Sections 17, 12.4; FR-SEC-01; G-07).

Every sink that can echo data passes through here — today the JSON/ text log
formatters (MT-2.1-03), tomorrow any log-adjacent output. Over-redaction is
deliberate (RISK-14): a redacted diagnostic value costs nothing, a leaked
credential costs a token rotation.

Two layers together (MT-2.1-03 risk note): this content scrubbing *and* the
structural rule from MT-2.1-02 that the agent token is never a log field
(``Settings.__repr__`` redaction) — safety does not depend on pattern coverage
alone.

Truncation (Section 12.4: logs truncate attachment text): every scrubbed string
is capped at :data:`MAX_SCRUBBED_CHARS`, so attachment-derived text can never
bloat a log line.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

__all__ = [
    "MAX_SCRUBBED_CHARS",
    "is_content_key",
    "is_secret_key",
    "scrub_mapping",
    "scrub_text",
    "scrub_value",
]

MAX_SCRUBBED_CHARS = 2000
_REDACTED = "[REDACTED]"
_OMITTED = "[OMITTED]"
_TRUNCATION_SUFFIX = "…[truncated]"

# Order matters: a bearer token carries its secret in the second token, so a
# key/value pass would only eat the scheme name.
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+\S+")

# A secret-shaped *name* followed by `=` or `:` and then the value. The name
# matches liberally because this runs over free-form message text where the
# exact key is unknown.
_KEY_VALUE_PATTERN = re.compile(
    r"""(?ix)
    [A-Za-z0-9_.\-]*(
        authorization | password | passwd | secret | token |
        api[\-_]?key | apikey | credential | private[\-_]?key | access[\-_]?key
    )[A-Za-z0-9_.\-]*
    (\s*[=:]\s*)
    ("[^"]*"|'[^']*'|\S+)
    """
)

# Exact (or suffix-matched) structured field names denoting a credential.
_SECRET_KEY_NAMES = frozenset(
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
        "agent_token",
    }
)
_SECRET_KEY_SUFFIXES = (
    "_password",
    "_passwd",
    "_secret",
    "_token",
    "_credential",
    "_credentials",
)

# Field names carrying raw attachment content or prompt text (G-07: never in
# logs; MT-2.1-03: omitted, not merely truncated).
_CONTENT_KEY_NAMES = frozenset(
    {
        "prompt",
        "prompt_text",
        "raw_prompt",
        "attachment",
        "attachment_content",
        "file_content",
        "patch",
        "diff",
        "body",
        "content",
    }
)
_CONTENT_KEY_SUFFIXES = ("_content", "_prompt")


def is_secret_key(key: str) -> bool:
    """Whether a structured field name denotes a credential (redact fully)."""
    lowered = key.lower()
    return lowered in _SECRET_KEY_NAMES or lowered.endswith(_SECRET_KEY_SUFFIXES)


def is_content_key(key: str) -> bool:
    """Whether a structured field name carries raw content (omit fully)."""
    lowered = key.lower()
    return lowered in _CONTENT_KEY_NAMES or lowered.endswith(_CONTENT_KEY_SUFFIXES)


def scrub_text(text: str) -> str:
    """Redact secret-shaped values in *text*, then cap its length."""
    result = _BEARER_PATTERN.sub(_REDACTED, text)
    result = _KEY_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{_REDACTED}", result
    )
    if len(result) > MAX_SCRUBBED_CHARS:
        result = result[:MAX_SCRUBBED_CHARS] + _TRUNCATION_SUFFIX
    return result


def scrub_value(key: str, value: object) -> object:
    """Scrub one structured value: by key first (secret > content), then text."""
    if is_secret_key(key):
        return _REDACTED
    if is_content_key(key):
        return _OMITTED
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, Mapping):
        return {str(item_key): scrub_value(str(item_key), item) for item_key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [scrub_value(key, item) for item in value]
    return value


def scrub_mapping(mapping: Mapping[str, object]) -> dict[str, object]:
    """Scrub every entry of a structured payload."""
    return {str(key): scrub_value(str(key), value) for key, value in mapping.items()}
