"""Correlation-id context for one request scope (Section 17; headers.md).

The canonical header name, honor-or-generate rule and propagation semantics
are fixed by ``docs/plan/conventions/headers.md`` (MT-0.5-03); this module is
the backend implementation. A contextvar (not thread-locals) so the id is
correct for thread- and async-based servers alike, and so every log line and
the error envelope read exactly the id of their own request scope.
"""

from __future__ import annotations

import re
from contextvars import ContextVar, Token
from uuid import uuid4

# Header spellings are case-insensitive on the wire; this is the documented
# spelling (headers.md: exactly one canonical name, no aliases).
CORRELATION_HEADER = "X-Correlation-ID"

# Defensive bounds on an *incoming* value: honor it only if it looks like an
# opaque diagnostic token (headers.md: never parsed for identity, but also
# never a vector for log injection or oversized echoes). Anything else is
# replaced by a freshly generated id — the honor-or-generate rule itself is
# unchanged for well-formed values.
_INCOMING_ID_PATTERN = re.compile(r"\A[A-Za-z0-9._:-]{1,128}\Z")

_correlation_id_var: ContextVar[str] = ContextVar("orchestrator_correlation_id", default="")


def new_correlation_id() -> str:
    """Generate an opaque id in the plan's example shape (Section 9.2)."""
    raw = uuid4().hex
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def resolve_incoming_id(incoming: str) -> str:
    """Honor a well-formed incoming value; generate one otherwise."""
    if _INCOMING_ID_PATTERN.fullmatch(incoming):
        return incoming
    return new_correlation_id()


def set_correlation_id(correlation_id: str) -> Token[str]:
    """Install *correlation_id* for the current scope; return the reset token."""
    return _correlation_id_var.set(correlation_id)


def get_correlation_id() -> str:
    """The current scope's id, or ``""`` outside any request scope."""
    return _correlation_id_var.get()


def reset_correlation_id(token: Token[str]) -> None:
    """Restore the scope to its previous value (always run in a ``finally``)."""
    _correlation_id_var.reset(token)
