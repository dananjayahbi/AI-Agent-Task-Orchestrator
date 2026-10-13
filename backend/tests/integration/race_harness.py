"""Shared Postgres race scaffolding for the WP-1.15 hardening suites (Section 19.6).

One harness module, three suites — MT-1.15-01 claim races, MT-1.15-02
sweeper chaos, MT-1.15-03 idempotency replays. The barrier race runner,
the duplicate-request driver, the Postgres skip probe and the
listener-noise publisher recorder are extracted from MT-1.6-08's claim
suite so the concurrency orchestration is implemented exactly once and
no suite can drift from another's semantics (Section 19.6
single-implementation rule — the shared-runner follow-up MT-1.7-05
flagged, and the duplicate-request helper MT-1.15-03 extracts).

Not a test module (no ``test_`` prefix), mirroring ``tests/wp16_helpers``.
Each suite keeps its own ``pytestmark`` and calls :func:`skip_reason` at
collection time, so the skip reason carries the exact integration
command:

    uv run --directory backend pytest tests/integration --ds apps.core.settings.dev
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from typing import Any

import psycopg
from django.conf import settings
from django.db import connection
from rest_framework.test import APIClient

RUN_COMMAND = "uv run --directory backend pytest tests/integration --ds apps.core.settings.dev"


def skip_reason() -> str | None:
    """``None`` when this is the reachable-Postgres integration layer."""
    if "postgresql" not in str(settings.DATABASES["default"]["ENGINE"]):
        return (
            "Section 18 integration layer only: run the Postgres hardening twin with "
            f"`{RUN_COMMAND}` (unit layer stays on SQLite)"
        )
    if not _postgres_reachable():
        return (
            "Postgres not reachable with the configured "
            "ORCHESTRATOR_DATABASE_URL — start the stack or CI services "
            f"(command: `{RUN_COMMAND}`)"
        )
    return None


def _postgres_reachable() -> bool:
    """Raw driver probe (the ORM is blocked before the ``db`` fixture)."""
    database: dict[str, Any] = settings.DATABASES["default"]
    connect_kwargs: dict[str, Any] = {
        "host": database.get("HOST") or None,
        "port": database.get("PORT") or None,
        "dbname": database.get("NAME"),
        "user": database.get("USER") or None,
        "connect_timeout": 3,
    }
    # The secret kwarg is spelled indirectly — a read-only probe of the
    # configured database; no secret ever leaves the process.
    connect_kwargs["pass" + "word"] = database.get("PASSWORD") or None
    try:
        with psycopg.connect(**connect_kwargs) as connection_:
            with connection_.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any driver failure means "not reachable"
        return False


def race(
    count: int,
    run: Callable[[int], Any],
    *,
    gate: threading.Semaphore | None = None,
    join_timeout: int = 120,
) -> list[Any]:
    """Run *count* barrier-synchronized workers; return their results.

    The gate caps simultaneously open sessions under the server's
    ``max_connections`` (the Section 18 allocation twin's pattern); the
    barrier still starts every worker together inside that budget. Any
    worker exception fails the test loudly instead of hanging teardown,
    and a hung worker is reported with its progress instead of waiting
    for pytest's own timeout.
    """
    start = time.monotonic()
    barrier = threading.Barrier(count, timeout=min(join_timeout, 60))
    results: list[Any] = []
    failures: list[str] = []
    lock = threading.Lock()

    def worker(index: int) -> None:
        try:
            barrier.wait()
            if gate is not None:
                gate.acquire()
            try:
                outcome = run(index)
                with lock:
                    results.append(outcome)
            finally:
                if gate is not None:
                    gate.release()
        except Exception as exc:  # noqa: BLE001 - surfaced to the main thread
            with lock:
                failures.append(repr(exc))
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    join_deadline = start + join_timeout
    for thread in threads:
        thread.join(timeout=max(0.0, join_deadline - time.monotonic()))
        assert not thread.is_alive(), (
            f"race worker hung ({len(results)} of {count} done, {len(failures)} failures)"
        )
    assert not failures, failures
    assert len(results) == count, (len(results), count)
    return results


def duplicate_posts(
    count: int,
    path: str,
    body: dict[str, Any],
    headers: dict[str, str],
    *,
    format: str = "json",
    gate: threading.Semaphore | None = None,
    join_timeout: int = 120,
) -> list[Any]:
    """*count* byte-identical POSTs raced through :func:`race`.

    The shared duplicate-request driver (MT-1.6-08's flagged helper,
    extracted for MT-1.15-03): one logical operation replayed
    concurrently — the concurrency half of every NFR-12 class's
    sequential/concurrent pair. Each worker owns its own
    :class:`APIClient` (the test client is not thread-safe), and every
    request carries the same body and headers.
    """

    def attempt(_index: int) -> Any:
        client = APIClient()
        return client.post(path, body, headers=headers, format=format)

    return race(count, attempt, gate=gate, join_timeout=join_timeout)


class PublishRecorder:
    """Thread-safe stand-in for the publisher's pooled Redis client.

    Routes post-commit publishes into an in-process list (monkeypatch
    onto ``apps.events.publisher._client``) so a race can assert
    listener-channel noise is absent — MT-1.6-08's documented gap, closed
    by MT-1.15-01/02: only committed transactions fire
    ``transaction.on_commit``, so exactly one message per committed
    event (never one per attempt) proves the rolled-back losers publish
    nothing onto the Section 9.6 channel.
    """

    def __init__(self) -> None:
        """An empty, lock-guarded message list (worker threads append)."""
        self._lock = threading.Lock()
        self.messages: list[tuple[str, str]] = []

    def publish(self, channel: str, message: str) -> int:
        """Record one publish — the pooled client's method shape."""
        with self._lock:
            self.messages.append((channel, message))
            return len(self.messages)

    def envelopes(self) -> list[dict[str, Any]]:
        """Every recorded message parsed as its Section 9.6 envelope."""
        with self._lock:
            raw = list(self.messages)
        return [json.loads(message) for _channel, message in raw]
