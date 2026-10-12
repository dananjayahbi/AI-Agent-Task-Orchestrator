"""MT-1.10-04 — 15-second heartbeat comments for proxy keep-alive.

Acceptance covered here (Sections 9.6, 15.4; RISK-05):

* an idle authenticated stream receives an SSE **comment** line at the
  configured cadence — the plan's 15 s default, made configurable
  (``ORCHESTRATOR_EVENTS_HEARTBEAT_SECONDS``) and driven short here to
  keep the suite fast and non-flaky (the MT's risk note);
* heartbeats carry no event id and no data — they can never advance a
  client's resume position or appear in the Event table;
* closing the connection cleans up: no lingering asyncio tasks/timers and
  the hub registration is gone (the wait is intrinsic to the stream
  generator, which the disconnect cancels — nothing else to leak).

Run with ``pytest backend/tests/events/test_heartbeat.py -v``.
"""

from __future__ import annotations

import asyncio

from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient

from apps.events.fanout import hub
from apps.events.models import Event

from .stream_helpers import create_event, envelope_of, open_owner_client, open_stream

FAST = 0.05  # seconds — heartbeat cadence for tests (default stays 15 s)


@override_settings(EVENTS_HEARTBEAT_SECONDS=FAST)
def test_idle_stream_receives_heartbeat_comments(db: None, owner_api: APIClient) -> None:
    """Silence on the queue → comment frames at the configured cadence."""
    del owner_api

    async def scenario() -> None:
        client = await open_owner_client()
        stream = await open_stream(client)
        try:
            for _ in range(3):
                frame = await stream.read_frame(timeout=2.0)
                assert frame.comment == "heartbeat", frame
                assert frame.event_id is None, "comments carry no id (9.6)"
                assert frame.data is None, "comments carry no event data (9.6)"
        finally:
            await stream.aclose()

    async_to_sync(scenario)()


@override_settings(EVENTS_HEARTBEAT_SECONDS=FAST)
def test_heartbeat_is_exactly_an_sse_comment_line(db: None, owner_api: APIClient) -> None:
    """Raw bytes: the frame is ``: heartbeat`` + blank line, nothing else."""
    del owner_api

    async def scenario() -> None:
        client = await open_owner_client()
        stream = await open_stream(client)
        try:
            raw = await stream._next_chunk(2.0)
            assert raw == b": heartbeat\n\n"
        finally:
            await stream.aclose()

    async_to_sync(scenario)()


@override_settings(EVENTS_HEARTBEAT_SECONDS=FAST)
def test_heartbeats_never_advance_the_resume_position(db: None, owner_api: APIClient) -> None:
    """Resume stays exactly where the client's last *event* id is."""
    del owner_api

    async def scenario() -> None:
        first = await create_event()
        client = await open_owner_client()
        stream1 = await open_stream(client)
        try:
            # Two heartbeats, then one real event.
            await stream1.read_frame(timeout=2.0)
            await stream1.read_frame(timeout=2.0)
            hub.broadcast(envelope_of(first))
            got = await stream1.read_events(1)
            assert [item["id"] for item in got] == [first.pk]
        finally:
            await stream1.aclose()  # the kill

        # A client whose "last id" is still 0 replays everything — the
        # heartbeats it received moved no server-side position, and no
        # Event row was written for them.
        second = await create_event()
        stream2 = await open_stream(client, headers={"Last-Event-ID": "0"})
        try:
            replayed = await stream2.read_events(2)
            assert [item["id"] for item in replayed] == [first.pk, second.pk]
        finally:
            await stream2.aclose()

    async_to_sync(scenario)()


@override_settings(EVENTS_HEARTBEAT_SECONDS=FAST)
def test_closing_the_stream_cleans_up_every_task(db: None, owner_api: APIClient) -> None:
    """No timer/task leaks: the post-close task set gains nothing pending."""
    del owner_api

    async def scenario() -> None:
        client = await open_owner_client()
        current = asyncio.current_task()
        before = {task for task in asyncio.all_tasks() if task is not current}

        stream = await open_stream(client)
        await stream.read_frame(timeout=2.0)  # a heartbeat proves the wait ran
        await stream.aclose()

        assert hub.connection_count == 0, "the registration is gone"
        after = {task for task in asyncio.all_tasks() if task is not current and not task.done()}
        assert not after - before, f"leaked tasks: {after - before!r}"

    async_to_sync(scenario)()


def test_default_heartbeat_is_the_plans_fifteen_seconds() -> None:
    """Section 9.6 default (15 s) is the committed, documented value."""
    assert settings.EVENTS_HEARTBEAT_SECONDS == 15


@override_settings(EVENTS_HEARTBEAT_SECONDS=FAST)
def test_heartbeat_frame_never_reaches_history(db: None, owner_api: APIClient) -> None:
    """Heartbeats do not appear in the Event table (no rows, no ids)."""
    del owner_api

    async def scenario() -> None:
        client = await open_owner_client()
        stream = await open_stream(client)
        try:
            await stream.read_frame(timeout=2.0)
            await stream.read_frame(timeout=2.0)
            count = await sync_to_async(Event.objects.count)()
            assert count == 0
        finally:
            await stream.aclose()

    async_to_sync(scenario)()
