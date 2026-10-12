"""Helpers driving the SSE gateway over Django's ASGI test path (WP-1.10).

Why this exists: the stream is a long-lived async ``StreamingHttpResponse``.
Django's ``AsyncClient`` returns it right after the response start (headers
flushed, body untouched — the early-flush property MT-1.10-01 asserts), and
its ``streaming_content`` is an async iterator that must be consumed inside
an event loop. ``async_to_sync`` (from a sync test function) provides that
loop with the asgiref guarantee that thread-sensitive work — DRF's sync
view, every ORM call inside the generator's replay — runs back on the
**test's own thread**, so the pytest-django connection and its transaction
are the ones the endpoint sees. No test opens a second database thread.

``SseStream`` accumulates raw chunks and yields parsed frames: ``id:`` /
``data:`` pairs (event frames) or comment lines (heartbeats). Chunk
boundaries are arbitrary — parsing happens only at ``\n\n`` frame
boundaries, exactly as the SSE standard requires of a client.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from asgiref.sync import sync_to_async
from django.test import AsyncClient

from apps.events.envelope import event_envelope
from apps.events.models import Event, EventActorType

from .conftest import PASSWORD

STREAM_PATH = "/api/v1/events/stream"

#: Close-path bound: chunks discarded while draining a closing stream's
#: leftover queue before giving up on a clean generator cancel (queues in
#: these tests hold single digits; the bound is a safety net, not a policy).
_MAX_DRAIN_STEPS = 1000


def make_event(
    *,
    type: str = "task.updated",
    project_id: str = "PID00001",
    task_id: str | None = None,
    data: dict[str, Any] | None = None,
) -> Event:
    """One stored Event row, directly (delivery tests, not emission tests).

    Emission paths are WP-1.9's covered surface; the gateway consumes rows.
    Written synchronously so it always joins the test's own connection and
    transaction (never call this from inside a scenario without
    ``sync_to_async``).
    """
    return cast(
        Event,
        Event.objects.create(
            type=type,
            project_id=project_id,
            task_id=task_id,
            occurred_at=datetime.now(UTC),
            actor_type=EventActorType.SYSTEM,
            actor_ref="wp110-tests",
            data=data or {},
            correlation_id="wp110-test-correlation",
        ),
    )


def envelope_of(event: Event) -> dict[str, Any]:
    """The exact JSON payload the publisher puts on the Redis channel."""
    return event_envelope(event)


async def create_event(**kwargs: Any) -> Event:
    """``make_event`` from inside a scenario (thread-sensitive → test thread).

    Django's sync-unsafe guard refuses ORM calls on the loop thread; the
    default ``sync_to_async`` executor is asgiref's *thread-sensitive*
    one — the test's own thread — so pytest-django's connection and
    transaction are the ones the row joins.
    """
    return await sync_to_async(make_event)(**kwargs)


@dataclass
class SseFrame:
    """One parsed SSE frame: an event (id + data) or a heartbeat comment."""

    event_id: int | None = None
    data: dict[str, Any] | None = None
    comment: str | None = None

    @property
    def is_event(self) -> bool:
        """True for a data frame; False for a comment (heartbeat)."""
        return self.data is not None


class SseStream:
    """One open SSE response: buffered parsing + bounded reads.

    ``open_stream`` leaves the response with **one outstanding read**
    (``prime``), which starts the view's async generator — the connection
    registers with the fan-out hub inside that first step. Reads await the
    outstanding pull through a shield, so a read *timeout* (negative
    assertions) never cancels the underlying generator, and ``aclose``
    cancels it so the generator's cleanup (unregister) always runs —
    even when the test never consumed a frame.
    """

    def __init__(self, response: Any) -> None:
        """Wrap a streaming test response (already past its status line)."""
        self.response = response
        self._iterator = response.streaming_content
        self._buffer = ""
        self._pending: asyncio.Future[bytes] | None = None

    def prime(self) -> None:
        """Start (do not await) the generator's first pull."""
        self._pull()

    def _pull(self) -> asyncio.Future[bytes]:
        """The single outstanding read: created on demand, reused by waits."""
        if self._pending is None:
            self._pending = asyncio.ensure_future(anext(self._iterator))
        return self._pending

    async def read_frame(self, timeout: float = 5.0) -> SseFrame:
        """Return the next complete frame, waiting at most *timeout* seconds.

        Raises ``AssertionError`` if the stream ends or the deadline passes
        — a hanging test is worse than a failing one, and heartbeat tests
        tune the interval down instead of the timeout up.
        """
        while True:
            frame = self._pop_frame()
            if frame is not None:
                return frame
            self._buffer += (await self._next_chunk(timeout)).decode("utf-8")

    async def _next_chunk(self, timeout: float) -> bytes:
        """One raw chunk from the outstanding pull, shielded from timeouts."""
        task = self._pull()
        try:
            chunk = await asyncio.wait_for(asyncio.shield(task), timeout)
        except StopAsyncIteration as exc:  # pragma: no cover - failure path
            raise AssertionError("stream ended while a frame was expected") from exc
        except TimeoutError as exc:
            raise AssertionError(f"no SSE frame within {timeout}s") from exc
        finally:
            if task.done():
                self._pending = None
        return chunk

    async def read_events(self, count: int, timeout: float = 5.0) -> list[dict[str, Any]]:
        """The next *count* event payloads (comments skipped)."""
        events: list[dict[str, Any]] = []
        while len(events) < count:
            frame = await self.read_frame(timeout)
            if frame.is_event:
                assert frame.data is not None
                events.append(frame.data)
        return events

    async def aclose(self) -> None:
        """Close the connection (client disconnect → generator cleanup).

        Closing an async generator chain from the outside is subtler than
        it looks: async generators register **no** sync ``close`` method,
        so Django's response resource-closers never close the view
        generator — only *cancellation propagating into it* runs its
        ``finally`` (the hub unregister). Two cases:

        * a pull is in flight — the chain (outer wrapper → view
          generator) is suspended inside one awaited step; cancelling it
          raises inside the view generator at its queue wait;
        * at rest — every frame is parked at its own ``yield``; one fresh
          pull resumes the whole chain, and cancelling it *mid-await*
          lands the cancellation inside the view generator. Queued
          leftovers are drained (discarded) by the bounded retry loop.
        """
        pending, self._pending = self._pending, None
        if pending is not None and not pending.done():
            pending.cancel()
            try:
                await pending
            except (asyncio.CancelledError, StopAsyncIteration, RuntimeError):
                pass
        else:
            for _ in range(_MAX_DRAIN_STEPS):
                step: asyncio.Future[bytes] = asyncio.ensure_future(anext(self._iterator))
                await asyncio.sleep(0)  # resume the chain one step
                if not step.done():
                    step.cancel()
                    try:
                        await step
                    except (asyncio.CancelledError, StopAsyncIteration, RuntimeError):
                        pass
                    break
                # A still-queued chunk was consumed and discarded; retry.
        await self._iterator.aclose()
        self.response.close()

    def _pop_frame(self) -> SseFrame | None:
        """Parse one ``\n\n``-terminated frame from the buffer, else None."""
        while "\n\n" in self._buffer:
            block, self._buffer = self._buffer.split("\n\n", 1)
            frame = self._parse(block)
            if frame is not None:
                return frame
        return None

    @staticmethod
    def _parse(block: str) -> SseFrame | None:
        """One frame block → SseFrame; blank blocks are skipped, not errors."""
        event_id: int | None = None
        data_lines: list[str] = []
        comment: str | None = None
        for line in block.split("\n"):
            if not line:
                continue
            if line.startswith(":"):
                comment = line[1:].lstrip()
            elif line.startswith("id:"):
                event_id = int(line[3:].strip())
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if event_id is None and not data_lines and comment is None:
            return None
        data = json.loads("\n".join(data_lines)) if data_lines else None
        return SseFrame(event_id=event_id, data=data, comment=comment)


async def open_stream(
    client: AsyncClient,
    *,
    path: str = STREAM_PATH,
    headers: dict[str, str] | None = None,
) -> SseStream:
    """GET the stream; assert the 200; return the readable connection.

    The stream is left *primed*: one pull is in flight and one loop
    iteration has run, so the view's generator has started (connection
    registered with the hub) before the caller broadcasts anything.
    """
    response = await client.get(path, headers=headers or {})
    assert response.status_code == 200, (
        response.status_code,
        response.content if not response.streaming else b"<streaming body>",
    )
    stream = SseStream(response)
    stream.prime()
    await asyncio.sleep(0)  # let the generator's first step run
    return stream


async def open_owner_client() -> AsyncClient:
    """A fresh AsyncClient logged in as the owner (cookie transport)."""
    client = AsyncClient()
    response = await client.post(
        "/api/v1/auth/login",
        {"username": "owner", "password": PASSWORD},
    )
    assert response.status_code == 200, response.content
    return client


__all__ = [
    "PASSWORD",
    "STREAM_PATH",
    "SseFrame",
    "SseStream",
    "create_event",
    "envelope_of",
    "make_event",
    "open_owner_client",
    "open_stream",
]
