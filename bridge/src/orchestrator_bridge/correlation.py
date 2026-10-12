"""Correlation-id scope for the bridge (parent plan Section 17; headers.md; MT-2.1-03).

The canonical header spelling (``X-Correlation-ID``) and the honor-or-generate
rule are fixed by ``docs/plan/conventions/headers.md`` — this module is the
bridge-side implementation of that contract.

Two id spaces stay separate (MT-2.1-03 risk note): ``correlation_id`` (this
scope) identifies one logical exchange for diagnostics, while MCP JSON-RPC
request ids belong to the wire protocol and are never logged as correlation ids.

Lifecycle: the entry points install a process-scope id at startup via
:func:`init_from_env` — the ``ORCHESTRATOR_CORRELATION_ID`` value is honored when
well-formed, otherwise a fresh id is generated (headers.md). WP-2.9 will
re-scope per connection and WP-2.3 reads :func:`get_correlation_id` to send the
``X-Correlation-ID`` header, so one agent action is reconstructable from both
the bridge's and the backend's logs (Section 17).
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from contextvars import ContextVar, Token
from uuid import uuid4

__all__ = [
    "CORRELATION_ENV_VAR",
    "CORRELATION_HEADER",
    "get_correlation_id",
    "init_from_env",
    "new_correlation_id",
    "reset_correlation_id",
    "resolve_incoming_id",
    "set_correlation_id",
]

# One canonical spelling, no aliases (headers.md; Section 0.4).
CORRELATION_HEADER = "X-Correlation-ID"
# Runtime scope input, not a persistent setting — documented in bridge/.env.example.
CORRELATION_ENV_VAR = "ORCHESTRATOR_CORRELATION_ID"

# Bounds on an incoming value: honor it only as an opaque diagnostic token —
# never parsed for identity, but never a vector for log injection either.
_INCOMING_ID_PATTERN = re.compile(r"\A[A-Za-z0-9._:-]{1,128}\Z")

_correlation_id_var: ContextVar[str] = ContextVar("orchestrator_bridge_correlation_id", default="")


def new_correlation_id() -> str:
    """Generate an opaque id in the plan's example shape (Section 9.2)."""
    raw = uuid4().hex
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def resolve_incoming_id(incoming: str) -> str:
    """Honor a well-formed incoming value; generate one otherwise (headers.md)."""
    if _INCOMING_ID_PATTERN.fullmatch(incoming):
        return incoming
    return new_correlation_id()


def set_correlation_id(correlation_id: str) -> Token[str]:
    """Install *correlation_id* for the current scope; return the reset token."""
    return _correlation_id_var.set(correlation_id)


def get_correlation_id() -> str:
    """The current scope's id, or ``""`` outside any installed scope."""
    return _correlation_id_var.get()


def reset_correlation_id(token: Token[str]) -> None:
    """Restore the scope to its previous value (always run in a ``finally``)."""
    _correlation_id_var.reset(token)


def init_from_env(env: Mapping[str, str] | None = None) -> Token[str]:
    """Install the process-scope id at startup; returns a token for tests.

    ``ORCHESTRATOR_CORRELATION_ID`` is honored when well-formed, generated when
    absent, empty or malformed (headers.md honor-or-generate) — every bridge log
    line of this run then carries a correlation id.
    """
    environ = os.environ if env is None else env
    incoming = environ.get(CORRELATION_ENV_VAR, "").strip()
    return set_correlation_id(resolve_incoming_id(incoming))
