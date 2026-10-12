"""MT-1.6-08 — the claim races on **real Postgres** (Section 18; NFR-01).

Postgres twin of the unit-layer claim suites: SQLite's single-writer
table lock cannot exercise ``select_for_update(skip_locked=True)`` (a
silent no-op there), so the race proofs live here:

* **NFR-01** — 50 concurrent claims of one task → *exactly one winner*,
  49 ``TASK_ALREADY_CLAIMED``, one lease (service level **and** the
  ``POST /tasks/{id}/claim`` endpoint with real credentials);
* the next-available disjointness race (Section 9.3 last paragraph):
  concurrent selectors never receive the same task;
* the cross-task concurrency limit (MT-1.6-06 / FR-LEA-08): with
  ``max_concurrent_tasks=1`` and two different tasks racing, the
  project-row mutex admits exactly one and answers the other
  ``CONCURRENCY_LIMIT_REACHED`` — a serialization only a locking
  backend can prove;
* the same-``Idempotency-Key`` race (NFR-12): many identical requests,
  exactly one lease, replayed bodies byte-identical;
* claim/release interleavings keep the Section 8.3 invariants: every
  claim paired with a release, generation counts the leases, version
  counts the transitions.

Skipped automatically when the active settings are not the integration
layer (unit job: SQLite per Section 18) or Postgres is unreachable —
the skip reason carries the exact command:

    uv run --directory backend pytest tests/integration --ds apps.core.settings.dev

Run with that command against CI's provisioned services (the
``integration-tests`` job) or a local Compose stack. Every test marks
``transaction=True`` so worker threads see committed rows on their own
connections.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from django.conf import settings
from django.core.cache import cache
from django.db import OperationalError, connection
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.errors import TASK_ALREADY_CLAIMED
from apps.leases.claim import claim_next_available, claim_task
from apps.leases.exceptions import ConcurrencyLimitReached, TaskAlreadyClaimed
from apps.leases.release import release_task
from apps.tasks.models import Task, TaskState, TaskTransition
from tests.wp16_helpers import (  # noqa: F401  (restore_lease_registry is autouse)
    active_policy_project,
    make_pending_task,
    restore_lease_registry,
)

_RUN_COMMAND = "uv run --directory backend pytest tests/integration --ds apps.core.settings.dev"

PASSWORD = "wp16-race-1!"  # pragma: allowlist secret


def _skip_reason() -> str | None:
    """``None`` when this is the reachable-Postgres integration layer."""
    if "postgresql" not in str(settings.DATABASES["default"]["ENGINE"]):
        return (
            "Section 18 integration layer only: run the Postgres race twin with "
            f"`{_RUN_COMMAND}` (unit layer stays on SQLite)"
        )
    if not _postgres_reachable():
        return (
            "Postgres not reachable with the configured "
            "ORCHESTRATOR_DATABASE_URL — start the stack or CI services "
            f"(command: `{_RUN_COMMAND}`)"
        )
    return None


def _postgres_reachable() -> bool:
    """Raw driver probe (the ORM is blocked before the ``db`` fixture)."""
    database: dict[str, Any] = settings.DATABASES["default"]
    try:
        with psycopg.connect(
            host=database.get("HOST") or None,
            port=database.get("PORT") or None,
            dbname=database.get("NAME"),
            user=database.get("USER") or None,
            password=database.get("PASSWORD") or None,
            connect_timeout=3,
        ) as connection_:
            with connection_.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any driver failure means "not reachable"
        return False


pytestmark = [
    pytest.mark.skipif(
        _skip_reason() is not None,
        reason=_skip_reason() or "unreachable",
    )
]


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history and idempotency replays are process/cache state."""
    cache.clear()
    yield
    cache.clear()


# --- shared race plumbing ---------------------------------------------------


def _race(
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
    worker exception fails the test loudly instead of hanging teardown.
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


def _claim_or_lost(task_id: str, project_id: str, session_id: str, label: str) -> str:
    """One service-level claim attempt; OperationalErrors retry, business
    errors answer immediately (a failed statement rolls its txn back)."""
    deadline = time.monotonic() + 60
    while True:
        try:
            claim_task(
                task_id=task_id,
                session_id=session_id,
                worker_agent_id=label,
                caller_project_id=project_id,
            )
            return "won"
        except TaskAlreadyClaimed:
            return "lost"
        except OperationalError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.005)


def _issue_agent_token(owner_name: str, project_id: str, role: str = "coder") -> dict[str, Any]:
    """Mint a project-scoped agent token through the real Owner API."""
    User.objects.create_user(owner_name, None, PASSWORD)
    owner = APIClient()
    login = owner.post("/api/v1/auth/login", {"username": owner_name, "password": PASSWORD})
    assert login.status_code == 200, login.content
    issued = owner.post("/api/v1/tokens/agent", {"project_id": project_id, "scopes": [role]})
    assert issued.status_code == 201, issued.content
    payload = issued.json()
    # Concatenation, not an f-string: keeps bearer literals out of templates.
    return {"Authorization": "Bearer " + str(payload["token"])}


def _code(response: Any) -> str:
    """The catalog code of one standard envelope (five fields, asserted)."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])


# --- NFR-01: 50 claims of one task -----------------------------------------


@pytest.mark.django_db(transaction=True)
def test_fifty_concurrent_claims_yield_exactly_one_winner_on_postgres() -> None:
    """NFR-01, service level: 50 racing claimants, one lease, no others."""
    project = active_policy_project("PID00091")
    task = make_pending_task(project, 1)
    base_version = task.version

    results = _race(
        50,
        lambda i: _claim_or_lost(task.pk, project.pk, "sess_race_claim", f"race-coder-{i}"),
        gate=threading.Semaphore(40),
        join_timeout=180,
    )

    assert results.count("won") == 1, results.count("won")
    assert results.count("lost") == 49

    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS
    assert task.lease_generation == 1, "the losing claims must not burn generations"
    assert task.attempt_number == 1
    assert task.version == base_version + 1, "exactly one transition committed"
    assert TaskTransition.objects.filter(task=task).count() == 1


@pytest.mark.django_db(transaction=True)
def test_fifty_concurrent_endpoint_claims_answer_one_200_and_49_409() -> None:
    """NFR-01, API level: one 200, forty-nine 409 TASK_ALREADY_CLAIMED."""
    project = active_policy_project("PID00092")
    task = make_pending_task(project, 1)
    auth = _issue_agent_token("owner-race-ep", project.pk)
    path = f"/api/v1/tasks/{task.pk}/claim"

    def attempt(index: int) -> Any:
        client = APIClient()
        return client.post(
            path,
            {"session_id": f"sess_race_ep_{index}", "worker_agent_id": f"race-{index}"},
            headers=auth,
        )

    responses = _race(50, attempt, gate=threading.Semaphore(40), join_timeout=180)

    statuses = [response.status_code for response in responses]
    assert statuses.count(200) == 1, statuses
    assert statuses.count(409) == 49, statuses
    assert set(statuses) <= {200, 409}, f"no 404/500 leaks in the race: {statuses}"
    for response in responses:
        if response.status_code == 409:
            assert _code(response) == TASK_ALREADY_CLAIMED

    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS
    assert task.lease_generation == 1


# --- Section 9.3: next-available disjointness ------------------------------


@pytest.mark.django_db(transaction=True)
def test_concurrent_next_available_hands_out_each_task_at_most_once() -> None:
    """Concurrent selectors claim different tasks (or ``None``), never twice."""
    project = active_policy_project("PID00093", max_concurrent_tasks=10)
    tasks = [make_pending_task(project, index) for index in range(1, 7)]

    def attempt(index: int) -> str | None:
        deadline = time.monotonic() + 60
        while True:
            try:
                claimed = claim_next_available(
                    caller_project_id=project.pk,
                    session_id="sess_race_next",
                    worker_agent_id=f"race-next-{index}",
                )
                return None if claimed is None else claimed.pk
            except OperationalError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.005)

    handed = _race(6, attempt, join_timeout=120)

    winners = [pk for pk in handed if pk is not None]
    assert len(winners) == len(set(winners)), "a task was handed out twice"
    assert len(winners) == len(tasks), f"six offerable tasks, six selectors: {handed}"

    fresh = {row.pk: row.state for row in Task.objects.filter(project=project)}
    for task in tasks:
        expected = TaskState.IN_PROGRESS if task.pk in set(winners) else TaskState.PENDING
        assert fresh[task.pk] == expected, task.pk


# --- MT-1.6-06: the cross-task concurrency limit ---------------------------


@pytest.mark.django_db(transaction=True)
def test_concurrency_limit_admits_only_one_of_two_racing_claims() -> None:
    """``max_concurrent_tasks=1`` + project-row mutex: one wins, one 409."""
    project = active_policy_project("PID00094", max_concurrent_tasks=1)
    first = make_pending_task(project, 1)
    second = make_pending_task(project, 2)

    def attempt(index: int) -> str:
        task_id = first.pk if index % 2 == 0 else second.pk
        deadline = time.monotonic() + 60
        while True:
            try:
                claim_task(
                    task_id=task_id,
                    session_id="sess_race_limit",
                    worker_agent_id=f"race-limit-{index}",
                    caller_project_id=project.pk,
                )
                return "won"
            except ConcurrencyLimitReached:
                return "limited"
            except TaskAlreadyClaimed:  # pragma: no cover - different tasks
                return "lost"
            except OperationalError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.005)

    results = _race(2, attempt, join_timeout=120)

    assert results.count("won") == 1, results
    assert results.count("limited") == 1, results

    states = dict(Task.objects.filter(project=project).values_list("pk", "state"))
    assert sorted(states.values()) == [TaskState.IN_PROGRESS, TaskState.PENDING]


# --- NFR-12: the same-Idempotency-Key race ---------------------------------


@pytest.mark.django_db(transaction=True)
def test_same_idempotency_key_race_creates_exactly_one_lease() -> None:
    """Many identical keyed requests → one lease; every replay identical."""
    project = active_policy_project("PID00095")
    task = make_pending_task(project, 1)
    auth = _issue_agent_token("owner-race-idem", project.pk)
    path = f"/api/v1/tasks/{task.pk}/claim"
    headers = {**auth, "Idempotency-Key": "race-key-1"}
    body = {"session_id": "sess_race_idem", "worker_agent_id": "race-idem"}

    def attempt(index: int) -> Any:
        client = APIClient()
        return client.post(path, body, headers=headers)

    responses = _race(20, attempt, gate=threading.Semaphore(20), join_timeout=120)

    statuses = [response.status_code for response in responses]
    assert set(statuses) <= {200, 409}, statuses
    assert 200 in statuses, statuses
    won = [response.json() for response in responses if response.status_code == 200]
    assert all(single == won[0] for single in won), "replays must be identical"
    for response in responses:
        if response.status_code == 409:
            assert _code(response) == TASK_ALREADY_CLAIMED

    task.refresh_from_db()
    assert task.lease_generation == 1, "the key race must produce exactly one lease"
    assert TaskTransition.objects.filter(task=task).count() == 1

    # Sequential retry after the race: byte-identical replay (NFR-12).
    retry = APIClient().post(path, body, headers=headers)
    assert retry.status_code == 200
    assert retry.json() == won[0]


# --- Section 8.3: claim/release interleavings ------------------------------


@pytest.mark.django_db(transaction=True)
def test_claim_release_interleavings_keep_the_section_8_3_invariants() -> None:
    """Racing claim→release pairs: generations, transitions and version
    all count exactly the committed work — no lost update, no orphan."""
    project = active_policy_project("PID00096")
    task = make_pending_task(project, 1)
    base_version = Task.objects.get(pk=task.pk).version

    def attempt(index: int) -> str:
        session = f"sess_race_pair_{index}"
        label = f"race-pair-{index}"
        deadline = time.monotonic() + 60
        while True:
            try:
                claimed = claim_task(
                    task_id=task.pk,
                    session_id=session,
                    worker_agent_id=label,
                    caller_project_id=project.pk,
                )
                break
            except TaskAlreadyClaimed:
                return "skipped"
            except OperationalError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.005)
        release_task(
            task_id=task.pk,
            session_id=session,
            lease_generation=claimed.lease_generation,
            actor_type="agent",
            actor_ref=session,
            caller_project_id=project.pk,
        )
        return "paired"

    results = _race(8, attempt, join_timeout=120)

    paired = results.count("paired")
    assert paired >= 1, results

    fresh = Task.objects.get(pk=task.pk)
    assert fresh.state == TaskState.PENDING, "every winner released before exiting"
    assert fresh.lease_generation == paired, "generation counts the leases"
    assert fresh.version == base_version + 2 * paired, "one bump per transition"

    transitions = TaskTransition.objects.filter(task=fresh)
    assert transitions.filter(to_state=TaskState.IN_PROGRESS).count() == paired
    assert transitions.filter(to_state=TaskState.PENDING).count() == paired
