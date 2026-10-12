"""Post-commit publish to the Redis channel (Section 9.6; MT-1.9-03).

Section 9.6: "Every state-changing action writes an Event row; after
commit it is published to a Redis channel." The SSE gateway (WP-1.10)
subscribes to that channel for live fan-out — so this module runs
**only** from ``transaction.on_commit`` callbacks (registered by
``apps.events.services.write_event``), never while a transaction is
open: subscribers can never observe an event that later rolled back.

Failure behavior (MT-1.9-03 acceptance): a publish failure — Redis
down, timeout, serialization surprise — is logged and swallowed. The
request that produced the event has already committed; the Event row
remains the source of truth and durability for anything missed live is
the DB-based resume of MT-1.10-03, not a publisher retry loop (out of
scope here).

Configuration (Section 9.10, env-driven with documented defaults):
``ORCHESTRATOR_EVENTS_CHANNEL`` for the channel name and
``ORCHESTRATOR_EVENTS_REDIS_URL`` for the connection, which falls back
to the cache Redis so Compose needs no new wiring (configuration.md
rows).

Ordering note for MT-1.10-02 (risk note): Redis does not order
concurrent publishes — consumers must sort/filter by the monotonic
envelope ``id``, never by arrival order.
"""

from __future__ import annotations

import json
import logging

import redis
from django.conf import settings

from .envelope import event_envelope
from .models import Event

logger = logging.getLogger(__name__)

#: One pooled client per process, created on first publish.
_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    """Return the process-wide Redis client (lazy — nothing connects at boot)."""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.EVENTS_REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


def publish_event(event: Event) -> None:
    """Publish *event*'s Section 9.6 envelope to the configured channel.

    Never raises: the row is already committed, so any failure is logged
    (Section 17 structured logging carries the traceback) and the
    originating request stays successful — the Event row remains the
    source of truth for recovery and replay.
    """
    try:
        _get_client().publish(
            settings.EVENTS_CHANNEL,
            json.dumps(event_envelope(event), separators=(",", ":")),
        )
    except Exception:  # noqa: BLE001 - an outage must not fail a committed write
        logger.warning(
            "post-commit publish failed for event %s (%s); "
            "the Event row remains the source of truth",
            event.pk,
            event.type,
            exc_info=True,
        )
