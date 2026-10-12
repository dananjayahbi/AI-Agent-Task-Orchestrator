"""MT-1.10-06 — SSE delivery load test: publish-to-receipt p95 under 2 s.

The closing WP-1.10 acceptance (Section 19: "p95 delivery under 2 s
locally"; NFR-03). Deterministic, fixed counts (CI-safe, Section 20.4
item 1): nine concurrent connections with mixed `project`/`task` filters,
thirty committed events spread over ~0.6 s, every delivery timed from its
**publish point** — not commit — to client receipt, exactly as the MT's
risk note demands.

Transport modes (the MT prefers the real thing, the unit layer must run
hermetically — Section 18):

* **redis** — a reachable Redis on the configured
  ``ORCHESTRATOR_EVENTS_REDIS_URL`` lets the *real* pipeline run:
  ``publisher.publish_event`` → channel → the hub's subscriber task →
  fan-out → receipt. Preferred whenever available (locally: ``wp16-
  redis``), including the Compose topology.
* **in-process transport** — no Redis: the publish point is the fan-out
  boundary (``hub.broadcast``) and the subscriber is disabled. The
  measurement then covers everything after the publish seam. Re-running
  against the Compose stack (backend + Redis + database) is the gate
  follow-up recorded in the WP changelog.

The resume-during-load case: one victim connection drops mid-run,
reconnects with its last event id, catches up through the replay path and
continues live — its catch-up and every replayed delivery must land within
the same 2 s budget (Section 19 WP-1.10 acceptance).

Percentiles are printed as a JSON line with the run (mode, counts, p50 /
p95 / p99 / max in ms) and embedded in the assertion message, so CI logs
carry the measurement, not just the verdict.

Run with ``pytest backend/tests/perf/test_sse_delivery_load.py -v``.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, cast

import pytest
import redis as sync_redis
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings

from apps.accounts.models import User
from apps.events import fanout, publisher
from apps.events.fanout import hub
from tests.events.conftest import PASSWORD
from tests.events.stream_helpers import (
    SseStream,
    envelope_of,
    make_event,
    open_owner_client,
    open_stream,
)

# Fixed scenario numbers (documented thresholds — Section 20.4 item 1).
STEADY_STREAMS = 8
TOTAL_EVENTS = 30
VICTIM_DROP_AFTER = 10  # victim dies after receiving this many
VICTIM_REOPEN_AFTER = 20  # ...and reconnects once this many were published
PUBLISH_INTERVAL = 0.02  # seconds between publishes (~0.6 s of load)
FRAME_TIMEOUT = 10.0  # seconds — generous per-frame bound, not the budget
P95_BUDGET_SECONDS = 2.0  # NFR-03 / Section 19 WP-1.10 acceptance

FILTERS: tuple[dict[str, str | None], ...] = (
    {"project": "PID00001"},
    {"project": "PID00002"},
    {"project": None},
    {"task": "PID00001-T001"},
)


def _redis_reachable() -> bool:
    """Whether the configured events Redis answers PING (2 s budget)."""
    try:
        client = sync_redis.Redis.from_url(
            settings.EVENTS_REDIS_URL, socket_connect_timeout=2, socket_timeout=2
        )
        return bool(client.ping())
    except Exception:  # noqa: BLE001 - absence is a mode choice, not a failure
        return False


def _expected_count(rows: list[Any], filters: dict[str, str | None]) -> int:
    """Rows matching one stream's filters (mirrors StreamConnection.accepts)."""
    count = 0
    for row in rows:
        if filters.get("project") is not None and row.project_id != filters["project"]:
            continue
        if filters.get("task") is not None and row.task_id != filters["task"]:
            continue
        count += 1
    return count


def _percentile(sorted_values: list[float], p: float) -> float:
    """Linear-interpolation percentile of an ascending list."""
    if not sorted_values:
        return 0.0
    position = (len(sorted_values) - 1) * p / 100.0
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def test_sse_delivery_p95_under_two_seconds_locally(
    db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-03: publish-to-receipt p95 < 2 s under filtered concurrent load."""
    User.objects.create_user("owner", None, PASSWORD)

    real_redis = _redis_reachable()
    mode = "redis" if real_redis else "in-process transport (gate follow-up: rerun on Compose)"
    if not real_redis:
        monkeypatch.setattr(fanout, "_async_redis", lambda: None)

    # Deterministic rows up front (ids ascend with publication order).
    rows = []
    for index in range(TOTAL_EVENTS):
        project = "PID00001" if index % 2 == 0 else "PID00002"
        task = "PID00001-T001" if index % 3 == 0 else None
        rows.append(make_event(project_id=project, task_id=task))

    publish_times: dict[int, float] = {}
    latencies: list[float] = []  # every publish→receipt delivery, seconds
    replay_deliveries: list[int] = []  # ids replayed before their publish point
    finished: dict[str, float] = {}  # label → completion timestamp
    marks: dict[str, float] = {}  # named instants (victim reopen)
    report: dict[str, Any] = {}

    async def consume(stream: SseStream, expected: int, label: str) -> list[int]:
        """Read *expected* event frames; record receipt times per id."""
        seen: list[int] = []
        while len(seen) < expected:
            frame = await stream.read_frame(timeout=FRAME_TIMEOUT)
            if not frame.is_event:
                continue
            assert frame.event_id is not None
            assert frame.event_id not in seen, f"{label}: duplicate {frame.event_id}"
            seen.append(frame.event_id)
            started = publish_times.get(frame.event_id)
            if started is None:
                # Replay outran the test's publication schedule: the row was
                # committed (the DB is the source of truth) but the publish
                # point had not been reached yet — counted, not timed.
                replay_deliveries.append(frame.event_id)
            else:
                latencies.append(time.perf_counter() - started)
        finished[label] = time.perf_counter()
        return seen

    async def scenario() -> None:
        client = await open_owner_client()

        streams: list[tuple[str, SseStream, int]] = []
        for index in range(STEADY_STREAMS):
            filters = FILTERS[index % len(FILTERS)]
            path = "/api/v1/events/stream" + "".join(
                f"{'&' if i else '?'}{key}={value}"
                for i, (key, value) in enumerate(
                    (k, v) for k, v in filters.items() if v is not None
                )
            )
            stream = await open_stream(client, path=path)
            streams.append((f"steady-{index}", stream, _expected_count(rows, filters)))

        # The victim: unfiltered, drops mid-run, resumes via Last-Event-ID.
        victim = await open_stream(client)
        victim_first_segment = asyncio.create_task(
            consume(victim, VICTIM_DROP_AFTER, "victim-segment-1")
        )

        readers: list[asyncio.Task[list[int]]] = [
            asyncio.create_task(consume(stream, expected, label))
            for label, stream, expected in streams
        ]

        async def publish_one(row: Any) -> None:
            """Start the clock at the publish point (MT risk note)."""
            publish_times[row.pk] = time.perf_counter()
            if real_redis:
                # The real pipeline: post-commit publisher → channel →
                # the hub's subscriber task → fan-out.
                await sync_to_async(publisher.publish_event)(row)
            else:
                hub.broadcast(envelope_of(row))

        for index, row in enumerate(rows):
            if index == VICTIM_DROP_AFTER:
                # Its first segment is fully delivered; the client dies.
                await asyncio.wait_for(victim_first_segment, FRAME_TIMEOUT)
                await victim.aclose()
            if index == VICTIM_REOPEN_AFTER:
                segment = await asyncio.wait_for(victim_first_segment, FRAME_TIMEOUT)
                victim_last_id = segment[-1]
                victim = await open_stream(client, headers={"Last-Event-ID": str(victim_last_id)})
                marks["victim_reopen"] = time.perf_counter()
                readers.append(
                    asyncio.create_task(
                        consume(
                            victim,
                            TOTAL_EVENTS - VICTIM_DROP_AFTER,
                            "victim-resumed",
                        )
                    )
                )
            await publish_one(row)
            await asyncio.sleep(PUBLISH_INTERVAL)

        results = await asyncio.gather(*readers, return_exceptions=True)
        for result in results:
            assert not isinstance(result, BaseException), f"reader failed: {result!r}"
        ok_results = cast("list[list[int]]", results)

        # Bookkeeping: steady streams saw exactly their filtered counts; the
        # victim's resumed reader saw the full tail (replay + live) exactly
        # once — the resume-during-load case within the same budget.
        steady_seen = ok_results[: len(streams)]
        for (label, _stream, expected), seen in zip(streams, steady_seen, strict=True):
            assert len(seen) == expected, f"{label}: {len(seen)} != {expected}"
        victim_resumed = ok_results[len(streams)]
        victim_resumed_set = set(victim_resumed)
        assert len(victim_resumed_set) == len(victim_resumed), "victim: duplicates"
        expected_tail = {row.pk for row in rows[VICTIM_DROP_AFTER:]}
        assert victim_resumed_set == expected_tail, (
            "resume-during-load: no gaps (full tail), no duplicates"
        )

        await hub.aclose()  # cancels the (real) subscriber task

    async_to_sync(scenario)()

    latencies.sort()
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)
    worst = latencies[-1] if latencies else 0.0
    catchup = finished["victim-resumed"] - marks["victim_reopen"]
    report = {
        "mode": mode,
        "streams": STEADY_STREAMS + 1,
        "events": TOTAL_EVENTS,
        "deliveries": len(latencies),
        "replay_deliveries": len(replay_deliveries),
        "victim_catchup_ms": round(catchup * 1000, 2),
        "p50_ms": round(p50 * 1000, 2),
        "p95_ms": round(p95 * 1000, 2),
        "p99_ms": round(p99 * 1000, 2),
        "max_ms": round(worst * 1000, 2),
        "budget_ms": P95_BUDGET_SECONDS * 1000,
    }
    print(f"\nSSE delivery load test: {json.dumps(report)}")  # noqa: T201 - the run's record
    assert p95 < P95_BUDGET_SECONDS, f"p95 {p95 * 1000:.1f}ms >= budget: {report}"
    assert catchup < P95_BUDGET_SECONDS, (
        f"resume-during-load catch-up {catchup * 1000:.1f}ms >= budget: {report}"
    )
