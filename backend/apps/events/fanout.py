"""Redis fan-out to connected SSE subscribers (Sections 9.6, 9.10; MT-1.10-02).

ADR-002 fixes Redis pub/sub for one-way feeds; Section 9.6 fixes the topology:
committed events land on one channel, and **one shared subscription per
process** is fanned out to open connections in application code — connection
count never multiplies Redis subscriptions. This module is that layer:

* :class:`StreamConnection` — one connection's registration: its
  connect-time ``project``/``task`` filters, its in-flight queue, and the
  id-keyed de-duplication set that is the foundation of MT-1.10-03's
  resume (``claim`` marks an id as sent exactly once).
* :class:`Hub` — the process-wide registry. ``broadcast`` dispatches one
  published envelope to every *accepting* connection and to no other; a
  failing connection is dropped from dispatch without affecting the rest.
* the subscriber task — started lazily with the first stream, one
  ``pubsub`` for the process, JSON envelopes out of the channel and into
  ``Hub.broadcast``.

Ordering discipline (MT-1.9-03's risk note): Redis does not order
concurrent publishes — dispatch never sorts by arrival; the envelope ``id``
is the total order and ``claim`` de-duplicates by it. Fire-and-forget
(RISK note): pub/sub drops are recoverable only from the Event table
(DB-based resume, MT-1.10-03), so nothing here buffers for redelivery
beyond each connection's in-flight queue, drained by the stream loop.

Configuration (Section 9.10): the same documented rows the publisher uses —
``ORCHESTRATOR_EVENTS_CHANNEL`` / ``ORCHESTRATOR_EVENTS_REDIS_URL``
(configuration.md), no new environment surface.

Test seam (mirrors ``publisher._client``): :func:`_async_redis` builds the
async client; unit tests substitute a factory so the Section 18 unit layer
never dials a service, and one test counts subscriptions through a fake.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any

import redis.asyncio as aioredis
from django.conf import settings

from .permissions import StreamScope

logger = logging.getLogger(__name__)

#: De-dup window per connection: ordered set of delivered ids, pruned to
#: this bound so a very long-lived stream cannot grow it without limit
#: (entries older than the window are pruned; duplicates that old would
#: have to arrive later than 4096 newer deliveries — far beyond the
#: commit→publish lag any concurrent pair can produce).
DEDUP_WINDOW = 4096

#: Subscriber reconnect delay after a Redis error (Section 9.6 stays
#: fire-and-forget: the stream keeps serving replay/heartbeat while the
#: subscription re-establishes).
SUBSCRIBER_RETRY_SECONDS = 5.0

#: The Section 9.6 heartbeat: an SSE **comment** line (``:``-prefixed) — it
#: carries no event id, never advances a client's resume position and
#: never appears in the Event table (MT-1.10-04).
HEARTBEAT_COMMENT = b": heartbeat\n\n"


def sse_frame(envelope: Mapping[str, Any]) -> bytes:
    """One Section 9.6 envelope as one SSE frame: ``id:`` + ``data:`` + blank.

    The ``id:`` line is the monotonically increasing event id (Section 9.6)
    — what an EventSource records as its last-event-id for MT-1.10-03's
    resume — and the ``data:`` line is the envelope JSON exactly as the
    publisher serializes it (same ``event_envelope``, same separators: one
    wire shape across publish, history and stream; Section 20.5).
    """
    payload = json.dumps(envelope, separators=(",", ":"))
    return f"id: {envelope['id']}\ndata: {payload}\n\n".encode()


class StreamConnection:
    """One open stream's registration inside the hub.

    Filters are fixed at connect time (Section 9.6); ``accepts`` is the
    live-dispatch gate — connect-time filters **and** the per-event scope
    of MT-1.10-05 (``permissions.StreamScope``) — and ``claim``
    de-duplicates by monotonic id at send time: called by the stream loop
    for live frames and by the replay path for re-sent rows, so the
    handover of MT-1.10-03 delivers each id exactly once regardless of
    arrival order.
    """

    def __init__(
        self,
        *,
        project: str | None = None,
        task: str | None = None,
        scope: StreamScope | None = None,
    ) -> None:
        """Hold the connect-time filters/scope and create the in-flight queue."""
        self.project = project
        self.task = task
        self.scope = scope if scope is not None else StreamScope()
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        # Ordered set (dict-as-set, insertion order): delivered ids, pruned
        # oldest-first at DEDUP_WINDOW — the "has it already been sent" set.
        self._sent: dict[int, None] = {}

    def accepts(self, envelope: Mapping[str, Any]) -> bool:
        """Whether the envelope falls inside this connection's scope + filters."""
        if not self.scope.allows(envelope):
            return False
        if self.project is not None and envelope.get("project_id") != self.project:
            return False
        if self.task is not None and envelope.get("task_id") != self.task:
            return False
        return True

    def offer(self, envelope: dict[str, Any]) -> None:
        """Queue one *matching* envelope for the stream loop (drop others)."""
        if self.accepts(envelope):
            self.queue.put_nowait(envelope)

    def claim(self, envelope: Mapping[str, Any]) -> bool:
        """Mark *envelope*'s id delivered; False if it already was.

        Called at every delivery point **before** serialization to the
        socket (MT-1.10-05's risk note) — never after a partial send.
        """
        event_id = int(envelope["id"])
        if event_id in self._sent:
            return False
        self._sent[event_id] = None
        while len(self._sent) > DEDUP_WINDOW:
            self._sent.pop(next(iter(self._sent)))
        return True

    @property
    def delivered_count(self) -> int:
        """Number of ids in the de-dup window (test/diagnostic surface)."""
        return len(self._sent)


class Hub:
    """The process-wide registry: one Redis subscription, N connections.

    Register/unregister run from the view (sync request phase) and the
    stream generator's cleanup; ``broadcast`` runs on the event loop from
    the subscriber task (or directly in tests). Dispatch iterates a tuple
    copy, so a connection closing mid-broadcast cannot corrupt the walk.
    """

    def __init__(self) -> None:
        """Empty registry; the subscriber task starts with the first stream."""
        self._connections: dict[int, StreamConnection] = {}
        self._subscriber: asyncio.Task[None] | None = None

    def register(self, connection: StreamConnection) -> None:
        """Add one open stream to the fan-out."""
        self._connections[id(connection)] = connection

    def unregister(self, connection: StreamConnection) -> None:
        """Remove one closed stream — the cleanup every close must hit."""
        self._connections.pop(id(connection), None)

    @property
    def connection_count(self) -> int:
        """Registered connections (leak tests assert this returns to 0)."""
        return len(self._connections)

    @property
    def subscriber(self) -> asyncio.Task[None] | None:
        """The single subscriber task, if one has been started."""
        return self._subscriber

    def broadcast(self, envelope: dict[str, Any]) -> None:
        """Dispatch one published envelope to every accepting connection.

        A broken connection (queue error, closed consumer) is logged and
        skipped — one bad subscriber never disturbs the others (MT-1.10-02
        lifecycle acceptance).
        """
        for connection in tuple(self._connections.values()):
            try:
                connection.offer(envelope)
            except Exception:  # noqa: BLE001 - isolate one connection's failure
                logger.warning(
                    "fan-out dropped event %s for a connection",
                    envelope.get("id"),
                    exc_info=True,
                )

    def start_subscriber(self) -> None:
        """Start the single Redis subscription for this process (idempotent).

        Called from the first stream's generator — the first moment an
        event loop is guaranteed to be running. Repeated streams reuse the
        one task (Section 9.6 fan-out design; ADR-002).
        """
        if self._subscriber is not None and not self._subscriber.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # pragma: no cover - defensive: only called async
            logger.warning("fan-out subscriber started outside an event loop")
            return
        self._subscriber = loop.create_task(_run_subscriber(self))

    async def aclose(self) -> None:
        """Cancel the subscriber and drop all registrations (test/teardown)."""
        task = self._subscriber
        self._subscriber = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass  # the cancellation we requested — the task's own close
        self._connections.clear()


#: The process-wide hub (one subscription per process by construction).
hub = Hub()


def _async_redis() -> aioredis.Redis | None:
    """The async Redis client for the subscriber (lazily built per task).

    Same documented connection as the publisher
    (``ORCHESTRATOR_EVENTS_REDIS_URL`` → cache Redis fallback); connect
    timeouts are short so a down Redis logs and retries (SUBSCRIBER_RETRY_
    SECONDS) instead of wedging the first stream open. ``None`` is the
    unit-layer test seam: a substituted factory disables the subscriber
    without touching the rest of the fan-out (Section 18 hermetic runs).
    """
    return aioredis.from_url(
        settings.EVENTS_REDIS_URL,
        socket_connect_timeout=5,
        socket_timeout=None,
    )


async def _run_subscriber(hub_ref: Hub) -> None:
    """One shared subscription: channel messages → ``hub_ref.broadcast``.

    Survives Redis blips with the documented retry delay; cancelled only by
    ``Hub.aclose`` (tests/teardown) — production keeps it for the process
    lifetime. JSON errors in a message are logged and skipped: one bad
    payload must not kill the subscription.
    """
    client = _async_redis()
    if client is None:
        logger.debug("fan-out subscriber disabled (no Redis client available)")
        return
    try:
        pubsub = client.pubsub()
        await pubsub.subscribe(settings.EVENTS_CHANNEL)
        logger.info("fan-out subscribed to %s", settings.EVENTS_CHANNEL)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, (bytes, bytearray)):
                data = data.decode("utf-8")
            try:
                envelope = json.loads(data)
            except (TypeError, ValueError):
                logger.warning("fan-out ignoring a malformed channel message")
                continue
            hub_ref.broadcast(envelope)
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001 - outage is logged, retried, never fatal
        logger.warning(
            "fan-out subscriber failed; retrying in %ss",
            SUBSCRIBER_RETRY_SECONDS,
            exc_info=True,
        )
        await asyncio.sleep(SUBSCRIBER_RETRY_SECONDS)
        if not hub_ref.connection_count:
            return
        hub_ref.start_subscriber()


async def drain_queue(connection: StreamConnection, timeout: float) -> dict[str, Any] | None:
    """Next live envelope for *connection*, or ``None`` on heartbeat timeout.

    The stream loop's receive primitive: waits at most *timeout* seconds so
    the caller can emit a heartbeat comment on ``None`` (MT-1.10-04).
    """
    try:
        return await asyncio.wait_for(connection.queue.get(), timeout)
    except TimeoutError:
        return None


__all__ = [
    "DEDUP_WINDOW",
    "HEARTBEAT_COMMENT",
    "Hub",
    "StreamConnection",
    "drain_queue",
    "hub",
    "sse_frame",
]
