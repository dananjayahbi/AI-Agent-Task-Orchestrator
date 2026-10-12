"""MT-1.10-02 — Redis fan-out to connected stream subscribers.

Acceptance covered here (Sections 9.6, 9.10; ADR-002):

* a published envelope reaches every connected stream whose ``project``/
  ``task`` filters match it, and no stream whose filters exclude it;
* the process maintains a **single** Redis subscription regardless of
  connection count (one subscriber task, one ``pubsub().subscribe`` on the
  documented channel — asserted through the ``_async_redis`` factory seam);
* closing a stream unregisters it — repeated open/close cycles leave zero
  registrations, including closes that never consumed a frame;
* the dispatched payload is the unmodified Section 9.6 envelope (the same
  ``event_envelope`` projection the publisher serializes);
* out-of-order ids (concurrent-commit publishes) are delivered exactly
  once each, in arrival order — dispatch never assumes ordering
  (MT-1.9-03's risk note; ``id`` is the total order clients sort by).

Run with ``pytest backend/tests/events/test_fanout.py -v``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from asgiref.sync import async_to_sync
from django.conf import settings

from apps.events import fanout
from apps.events.fanout import hub

from .stream_helpers import (
    STREAM_PATH,
    create_event,
    envelope_of,
    make_event,
    open_owner_client,
    open_stream,
)

PROJECT_ONE_STREAM = f"{STREAM_PATH}?project=PID00001"
PROJECT_TWO_STREAM = f"{STREAM_PATH}?project=PID00002"


def test_matching_streams_receive_events_and_others_do_not(db: None, owner_api: Any) -> None:
    """Filter dispatch: each stream sees exactly its matching envelopes."""
    del owner_api  # creates the owner user; the async client logs in itself

    async def scenario() -> None:
        client = await open_owner_client()
        pid1 = await open_stream(client, path=PROJECT_ONE_STREAM)
        pid2 = await open_stream(client, path=PROJECT_TWO_STREAM)
        everything = await open_stream(client)

        first = await create_event(project_id="PID00001", task_id="PID00001-T001")
        second = await create_event(project_id="PID00002")
        hub.broadcast(envelope_of(first))
        hub.broadcast(envelope_of(second))

        got_pid1 = await pid1.read_events(1)
        assert [item["id"] for item in got_pid1] == [first.pk]

        got_pid2 = await pid2.read_events(1)
        assert [item["id"] for item in got_pid2] == [second.pk]

        got_all = await everything.read_events(2)
        assert [item["id"] for item in got_all] == [first.pk, second.pk]

        # The excluded event never arrives on the filtered stream.
        with pytest.raises(AssertionError, match="no SSE frame within"):
            await pid1.read_frame(timeout=0.1)

        for stream in (pid1, pid2, everything):
            await stream.aclose()

    async_to_sync(scenario)()


def test_one_shared_subscription_for_many_connections(
    db: None, owner_api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Five streams → one subscriber task, one subscribe on the channel."""
    counts: dict[str, int] = {"factory": 0, "subscribe": 0}
    channels_seen: list[str] = []

    class FakePubSub:
        """Records the subscribe; listens forever (cancellable)."""

        async def subscribe(self, channel: str) -> None:
            counts["subscribe"] += 1
            channels_seen.append(channel)

        async def listen(self) -> Any:
            while True:
                await asyncio.Event().wait()
            yield  # pragma: no cover - makes this an async generator

    class FakeRedis:
        """One pubsub object per (single) factory call."""

        def pubsub(self) -> FakePubSub:
            return FakePubSub()

    def factory() -> FakeRedis:
        counts["factory"] += 1
        return FakeRedis()

    monkeypatch.setattr(fanout, "_async_redis", factory)
    del owner_api

    async def scenario() -> None:
        client = await open_owner_client()
        streams = [await open_stream(client) for _ in range(5)]

        event = await create_event()
        hub.broadcast(envelope_of(event))
        for stream in streams:
            # Every stream's generator has started (start_subscriber ran)
            # and received the matching event.
            await stream.read_events(1)
        await asyncio.sleep(0)  # let the subscriber task take its first step

        assert counts["factory"] == 1, "one Redis client for the process"
        assert counts["subscribe"] == 1, "one subscription regardless of count"
        assert channels_seen == [settings.EVENTS_CHANNEL], "documented channel"
        assert hub.subscriber is not None and not hub.subscriber.done()

        await hub.aclose()  # cancels the fake subscriber — no dangling task
        for stream in streams:
            await stream.aclose()

    async_to_sync(scenario)()


def test_closing_streams_unregisters_them(db: None, owner_api: Any) -> None:
    """Repeated open/close cycles leak no registrations (lifecycle)."""
    del owner_api

    async def scenario() -> None:
        client = await open_owner_client()
        for cycle in range(3):
            stream = await open_stream(client)
            assert hub.connection_count == 1, cycle
            event = await create_event()
            hub.broadcast(envelope_of(event))
            await stream.read_events(1)
            await stream.aclose()
            assert hub.connection_count == 0, f"leak after cycle {cycle}"

        # A close that never consumed a frame still cleans up: aclose
        # cancels the primed pull, running the generator's finally.
        untouched = await open_stream(client)
        assert hub.connection_count == 1
        await untouched.aclose()
        assert hub.connection_count == 0

    async_to_sync(scenario)()


def test_dispatched_payload_is_the_published_envelope(db: None, owner_api: Any) -> None:
    """The frame's data equals the published Section 9.6 envelope exactly."""
    del owner_api
    event = make_event(
        type="task.transitioned",
        task_id="PID00001-T004",
        data={"from_state": "in_progress", "to_state": "pending"},
    )
    published = envelope_of(event)

    async def scenario() -> None:
        client = await open_owner_client()
        stream = await open_stream(client)
        hub.broadcast(dict(published))

        frame = await stream.read_frame()
        assert frame.event_id == event.pk == published["id"]
        assert frame.data == published, "unmodified envelope (Section 20.5)"
        assert set(frame.data or {}) == {
            "id",
            "type",
            "project_id",
            "task_id",
            "occurred_at",
            "actor",
            "data",
        }
        assert set((frame.data or {})["actor"]) == {"type", "ref"}
        await stream.aclose()

    async_to_sync(scenario)()


def test_out_of_order_ids_are_delivered_exactly_once(db: None, owner_api: Any) -> None:
    """Concurrent-commit publishes: arrival order, no drop, no duplicate."""
    del owner_api
    high, low = 5000, 4999  # published out of id order (Redis orders nothing)

    def synthetic(event_id: int) -> dict[str, Any]:
        return {
            "id": event_id,
            "type": "task.updated",
            "project_id": "PID00001",
            "task_id": None,
            "occurred_at": "2026-10-11T12:45:02Z",
            "actor": {"type": "system", "ref": "race"},
            "data": {},
        }

    async def scenario() -> None:
        client = await open_owner_client()
        stream = await open_stream(client)
        hub.broadcast(synthetic(high))
        hub.broadcast(synthetic(low))

        first = await stream.read_frame()
        second = await stream.read_frame()
        assert [first.event_id, second.event_id] == [high, low], (
            "dispatch does not reorder or drop — consumers sort by id"
        )
        # A third delivery of either id would be a duplicate — none arrives.
        with pytest.raises(AssertionError, match="no SSE frame within"):
            await stream.read_frame(timeout=0.1)
        await stream.aclose()

    async_to_sync(scenario)()


def test_subscriber_configuration_is_the_documented_default() -> None:
    """Section 9.10: the fan-out reads the same env rows as the publisher."""
    assert settings.EVENTS_CHANNEL == "orchestrator:events"
    assert settings.EVENTS_REDIS_URL.startswith(("redis://", "rediss://"))
