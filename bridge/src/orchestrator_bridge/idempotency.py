"""``Idempotency-Key`` generation for mutating calls (parent plan Sections 9.2,
10.10; headers.md; ADR-012; NFR-12; MT-2.3-03).

One canonical header spelling — ``Idempotency-Key`` — with no aliases
(headers.md; Section 0.4). The bridge sends it on **every** mutating request
(Section 10.10; headers.md defines mutating as all ``POST``/``PATCH``/
``PUT``/``DELETE`` calls) and never on reads.

Key contract (MT-2.3-03 scope):

* **One key per logical operation.** The key is minted when the client
  prepares a call — before any attempt — and the transport re-sends the
  identical header dict on every retry, so a retried claim/checkpoint/submit
  replays instead of re-executing (ADR-012's bridge half; tested by
  ``test_idempotency.py`` against the retry loop).
* **Distinct operations never share a key.** The shape is
  ``<process-nonce>-<sequence>-<operation>-<target>``: a per-run nonce plus
  an atomic sequence guarantee uniqueness inside a process, and across
  processes in practice — deterministic *within* a run as the MT requires,
  no material persisted (nothing to disk, nothing to a log line; the logging
  layer would also redact a field named ``key`` — defence in depth).
* **Header-safe by construction:** only ``[A-Za-z0-9._-]`` characters, capped
  at :data:`MAX_KEY_CHARS` (200 — comfortably under the usual 255-byte
  header/parameter limits; the prefix carries the uniqueness, so truncation
  only trims the human-readable tail).

Callers may pass an explicit key (``transport.exchange(...,
idempotency_key=...)``) when one logical operation spans several calls — the
default minting covers the common case of one call = one operation.
"""

from __future__ import annotations

import itertools
import re
import uuid
from typing import Final

__all__ = [
    "IDEMPOTENCY_HEADER",
    "MAX_KEY_CHARS",
    "is_mutating",
    "new_key",
]

#: The one canonical spelling (headers.md) — no ``X-Idempotency-Key`` alias.
IDEMPOTENCY_HEADER: Final = "Idempotency-Key"

#: Upper bound on a key's length (header-safety; uniqueness rides the prefix).
MAX_KEY_CHARS: Final = 200

#: headers.md: mutating = all POST, PATCH, PUT and DELETE endpoints.
_MUTATING_METHODS: Final[frozenset[str]] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: Read verbs never carry a key (kept explicit for the docstring/tests).
_NON_MUTATING_METHODS: Final[frozenset[str]] = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")

#: Per-process unique component — never persisted, never logged.
_PROCESS_NONCE: Final = uuid.uuid4().hex[:12]
#: Monotonic within the process (``itertools.count.__next__`` is atomic).
_SEQUENCE = itertools.count()


def is_mutating(method: str) -> bool:
    """Whether *method* must carry an ``Idempotency-Key`` (headers.md)."""
    verb = method.upper()
    if verb in _NON_MUTATING_METHODS:
        return False
    return verb in _MUTATING_METHODS


def _slug(text: str) -> str:
    return _SLUG_PATTERN.sub("-", text).strip("-.")


def new_key(operation: str, *, target: str | None = None) -> str:
    """Mint one key for one logical *operation* (optionally scoped to a *target*).

    ``transport`` passes the HTTP verb as *operation* and the request path as
    *target* — the path already names the resource, so a claim and a
    checkpoint on the same task fingerprint differently.
    """
    sequence = next(_SEQUENCE)
    fingerprint = _slug(operation)
    if target:
        fingerprint = f"{fingerprint}-{_slug(target)}"
    return f"{_PROCESS_NONCE}-{sequence:06d}-{fingerprint}"[:MAX_KEY_CHARS]
