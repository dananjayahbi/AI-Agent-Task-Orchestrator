"""MT-1.10-03 — lossless resume via Last-Event-ID (no gaps, no duplicates).

Acceptance covered here (Sections 9.6, 9.2; Section 19 WP-1.10):

* killing a client and reconnecting with its last id delivers every missed
  event **exactly once, in id order**, then live events — no gaps, no
  duplicates; replay and live frames carry the unchanged Section 9.6
  envelope;
* a fresh connection starts live without backfill (the documented reading
  — the plan does not mandate initial backfill);
* reconnect with the newest id replays nothing at all;
* a race during the replay→live handover (concurrently published copies of
  replayed ids plus one new id) loses nothing and duplicates nothing —
  registration-before-replay plus the shared ``claim`` gate make delivery
  exactly-once regardless of which copy arrives first;
* resume respects the connection's ``project``/``task`` filters on both
  the replay and the live handover;
* the resume input is the SSE ``Last-Event-ID`` header *or* the
  ``last_event_id`` query parameter (MT-4.3-04's transport note); a
  malformed value answers the canonical ``VALIDATION_ERROR`` before any
  stream opens.

Run with ``pytest backend/tests/events/test_resume.py -v``.
"""

from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import async_to_sync
from rest_framework.test import APIClient

from apps.events.fanout import hub

from .stream_helpers import (
    STREAM_PATH,
    create_event,
    envelope_of,
    open_owner_client,
    open_stream,
)

QUIET = 0.15  # seconds an "expects nothing more" read waits (no heartbeat yet)


def _code(response: Any) -> str:
    """Assert the canonical five-field envelope and return its code."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])


def test_kill_reconnect_delivers_missed_exactly_once_then_live(
    db: None, owner_api: APIClient
) -> None:
    """The Section 19 acceptance, verbatim: kill → reconnect → no gaps/dups."""
    del owner_api

    async def scenario() -> None:
        first = await create_event()
        second = await create_event()
        third = await create_event()

        client = await open_owner_client()
        # Mid-stream kill: one live delivery, then the client dies.
        stream1 = await open_stream(client)
        hub.broadcast(envelope_of(first))
        got = await stream1.read_events(1)
        assert [item["id"] for item in got] == [first.pk]
        await stream1.aclose()  # the kill

        # While disconnected: `second` was published (row committed, publish
        # lost to the dead subscriber — fire-and-forget per Section 9.6);
        # `third` too. Reconnect with the last received id replays both.
        stream2 = await open_stream(client, headers={"Last-Event-ID": str(first.pk)})
        replayed = await stream2.read_events(2)
        assert [item["id"] for item in replayed] == [second.pk, third.pk], (
            "missed events, once each, in id order"
        )
        assert replayed[0] == envelope_of(second), "unchanged Section 9.6 envelope"

        # ...then live delivery continues on the same connection.
        fourth = await create_event()
        hub.broadcast(envelope_of(fourth))
        live = await stream2.read_events(1)
        assert [item["id"] for item in live] == [fourth.pk]
        assert all(item["id"] != first.pk for item in replayed + live), (
            "no duplicate of the already-received id"
        )
        await stream2.aclose()

    async_to_sync(scenario)()


def test_fresh_connection_starts_live_without_backfill(db: None, owner_api: APIClient) -> None:
    """No last id → live only (documented reading); stored rows are not replayed."""
    del owner_api  # creates the owner user the scenario logs in as

    async def scenario() -> None:
        stale = await create_event()  # predates the connection
        client = await open_owner_client()
        stream = await open_stream(client)
        try:
            with pytest.raises(AssertionError, match="no SSE frame within"):
                await stream.read_frame(timeout=QUIET), "no backfill of stale rows"

            live = await create_event()
            hub.broadcast(envelope_of(live))
            got = await stream.read_events(1)
            assert [item["id"] for item in got] == [live.pk]
            assert got[0]["id"] != stale.pk
        finally:
            await stream.aclose()

    async_to_sync(scenario)()


def test_reconnect_with_the_newest_id_replays_nothing(db: None, owner_api: APIClient) -> None:
    """Last id = newest → zero replay frames; live continues normally."""
    del owner_api

    async def scenario() -> None:
        newest = await create_event()
        client = await open_owner_client()
        stream = await open_stream(client, headers={"Last-Event-ID": str(newest.pk)})
        try:
            try:
                await stream.read_frame(timeout=QUIET)
            except AssertionError:
                pass  # nothing replayed — exactly the gap the client had
            else:
                raise AssertionError("replayed past the newest id")

            live = await create_event()
            hub.broadcast(envelope_of(live))
            got = await stream.read_events(1)
            assert [item["id"] for item in got] == [live.pk]
        finally:
            await stream.aclose()

    async_to_sync(scenario)()


def test_resume_respects_the_connection_filters(db: None, owner_api: APIClient) -> None:
    """Replay and the live handover both honour project/task filters."""
    del owner_api

    async def scenario() -> None:
        mine1 = await create_event(project_id="PID00001", task_id="PID00001-T001")
        other = await create_event(project_id="PID00002")
        mine2 = await create_event(project_id="PID00001")

        client = await open_owner_client()
        stream = await open_stream(
            client, path=f"{STREAM_PATH}?project=PID00001", headers={"Last-Event-ID": "0"}
        )
        try:
            replayed = await stream.read_events(2)
            assert [item["id"] for item in replayed] == [mine1.pk, mine2.pk], (
                "the other project's row is never replayed"
            )

            cross_project = await create_event(project_id="PID00002")
            hub.broadcast(envelope_of(other))
            hub.broadcast(envelope_of(cross_project))
            matching = await create_event(project_id="PID00001")
            hub.broadcast(envelope_of(matching))
            got = await stream.read_events(1)
            assert [item["id"] for item in got] == [matching.pk], (
                "live handover drops the cross-project events too"
            )
        finally:
            await stream.aclose()

    async_to_sync(scenario)()


def test_race_during_handover_delivers_everything_once(db: None, owner_api: APIClient) -> None:
    """Concurrent publishes during replay: exactly-once, in id order."""
    del owner_api

    async def scenario() -> None:
        first = await create_event()
        second = await create_event()

        client = await open_owner_client()
        # Last-Event-ID=0 → the replay covers first and second; the copies
        # broadcast right after registration simulate publishes racing the
        # replay query (registration already happened inside open_stream).
        stream = await open_stream(client, headers={"Last-Event-ID": "0"})
        hub.broadcast(envelope_of(first))
        hub.broadcast(envelope_of(second))
        third = await create_event()
        hub.broadcast(envelope_of(third))

        try:
            got = await stream.read_events(3)
            assert [item["id"] for item in got] == [first.pk, second.pk, third.pk], (
                "handover: no gap (third arrives), no duplicate (copies deduped)"
            )
            try:
                await stream.read_frame(timeout=QUIET)
            except AssertionError:
                pass  # nothing further — duplicates would surface here
            else:
                raise AssertionError("duplicate delivery after the handover")
        finally:
            await stream.aclose()

    async_to_sync(scenario)()


def test_last_event_id_query_parameter_resumes(db: None, owner_api: APIClient) -> None:
    """Fetch/mobile clients that cannot set the header resume via query."""
    del owner_api

    async def scenario() -> None:
        seen = await create_event()
        missed = await create_event()
        client = await open_owner_client()
        stream = await open_stream(client, path=f"{STREAM_PATH}?last_event_id={seen.pk}")
        try:
            got = await stream.read_events(1)
            assert [item["id"] for item in got] == [missed.pk]
        finally:
            await stream.aclose()

    async_to_sync(scenario)()


def test_malformed_last_event_id_answers_validation_error(db: None, owner_api: APIClient) -> None:
    """Bad resume input: canonical 400 before any stream opens (9.2)."""
    for suffix in ("?last_event_id=banana", "?last_event_id=-1"):
        response = owner_api.get(STREAM_PATH + suffix)
        assert response.status_code == 400, suffix
        assert _code(response) == "VALIDATION_ERROR", suffix

    header_bad = owner_api.get(STREAM_PATH, headers={"Last-Event-ID": "nope"})
    assert header_bad.status_code == 400
    assert _code(header_bad) == "VALIDATION_ERROR"

    blank_header = owner_api.get(STREAM_PATH, headers={"Last-Event-ID": ""})
    assert blank_header.status_code == 200, "a blank header means a fresh stream"
