"""Idempotency-Key replay store (Section 9.2; ADR-012; NFR-12; MT-0.5-03).

The minimal exchange record headers.md fixes "so a retry can be confirmed
to be *the same request* before replaying":

1. the key, **in its request scope** — hashed together with method + path
   into the cache key, so one key on different endpoints are different
   records;
2. a fingerprint of the original request (method, path, body digest) —
   compared before replaying;
3. the original outcome (status + body) — what a retry replays;
4. a creation timestamp driving retention — the cache TTL below.

**Storage backend:** the Django cache (LocMem in the unit layer, Redis in
dev/prod — the composed ``ORCHESTRATOR_CACHE_URL``). Retention is a
module constant, **not a setting**: headers.md records the window as an
open point for owner confirmation ("the store's lifetime is an
implementation detail of WP-1.1 / WP-1.15 flagged for review — not a
contract"), so no configuration.md row exists yet; when the owner decides,
the constant moves into the Section 9.10 settings table.

**Scope of the guarantee (recorded, not invented):**

* only *successful* (2xx) outcomes are stored — a failed first attempt is
  executed again on retry (retryable failures are meant to be retried);
* **key reuse with a different request** — headers.md marks the response
  an open point ("no behavior or code is invented here"): this store
  simply does **not replay** (fingerprints differ) and executes the new
  request normally; no catalog code is emitted for the mismatch;
* concurrent same-key submits are not linearized here — the WP-1.15
  idempotency suite (MT-1.15-03) hardens this store; this implementation
  exists because MT-1.4-03 requires the replay behavior now.

``Idempotency-Key`` is the one canonical spelling — no aliases
(headers.md); callers of :func:`idempotency_key_of` read exactly that.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

from django.core.cache import cache
from django.http import HttpRequest

# headers.md: one canonical spelling, never X-Idempotency-Key et al.
IDEMPOTENCY_HEADER: Final = "Idempotency-Key"

# Retention window — open point (headers.md), implementation detail until
# the owner decides: 24 h, comfortably beyond any client's retry horizon.
IDEMPOTENCY_RETENTION_SECONDS: Final = 60 * 60 * 24

_CACHE_PREFIX: Final = "idempotency:"


def idempotency_key_of(request: HttpRequest) -> str | None:
    """The canonical header's value, or ``None`` when the call carries none."""
    value = request.headers.get(IDEMPOTENCY_HEADER)
    return value if value else None


def request_fingerprint(request: HttpRequest, body: Any) -> str:
    """Digest of (method, path, parsed body) — the "same request" test."""
    material = json.dumps(
        {
            "method": (request.method or "").upper(),
            "path": request.path,
            "body": body,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _cache_key(key: str, request: HttpRequest) -> str:
    """Key + request scope (method, path) hashed into one cache key."""
    scope = hashlib.sha256(
        f"{(request.method or '').upper()}\n{request.path}\n{key}".encode()
    ).hexdigest()
    return f"{_CACHE_PREFIX}{scope}"


def lookup_replay(request: HttpRequest, key: str, fingerprint: str) -> dict[str, Any] | None:
    """The stored outcome for this key+scope when it is the *same* request.

    Returns ``{"status": int, "body": ...}`` for replay, ``None`` for a
    miss — or for a fingerprint mismatch, which headers.md leaves open:
    the caller then executes normally (no replay, no invented error).
    """
    stored = cache.get(_cache_key(key, request))
    if not isinstance(stored, dict):
        return None
    if stored.get("fingerprint") != fingerprint:
        return None
    status = stored.get("status")
    if not isinstance(status, int):  # pragma: no cover - defensive
        return None
    return {"status": status, "body": stored.get("body")}


def store_outcome(
    request: HttpRequest,
    key: str,
    fingerprint: str,
    *,
    status: int,
    body: Any,
) -> None:
    """Record one successful outcome for later replays (2xx only)."""
    if not 200 <= status < 300:
        return
    cache.set(
        _cache_key(key, request),
        {
            "fingerprint": fingerprint,
            "status": status,
            # JSON round-trip: plain types only (LocMem pickles whatever it
            # gets; DRF ReturnDict must not leak into the cache).
            "body": json.loads(json.dumps(body, default=str)),
        },
        IDEMPOTENCY_RETENTION_SECONDS,
    )
