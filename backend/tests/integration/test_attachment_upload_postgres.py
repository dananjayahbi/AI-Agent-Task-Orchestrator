"""MT-1.11-02 — upload counters race on **real Postgres** (Section 18; risk note).

The unit layer (SQLite, single-writer) cannot exercise ``select_for_update`` —
a silent no-op there — so the MT-1.11-02 risk note's concurrency proof lives
here: the per-task count/total caps must be computed atomically at write time
or concurrent uploads overshoot them.

* **count cap** — many racing uploads of *distinct* bytes against one task
  with a reduced ``ATTACHMENT_MAX_PER_TASK``: exactly the cap's worth commits,
  every rejection answers ``VALIDATION_ERROR``, and the stored row count never
  exceeds the cap (no overshoot — the task row lock serializes the check).
* **total-bytes cap** — the same race against a reduced
  ``ATTACHMENT_MAX_TOTAL_BYTES``: the byte sum stops at or below the cap.
* **de-duplication race** — many racing uploads of *identical* bytes collapse
  onto **one** record and one stored object (Section 9.5: one de-dup probe per
  task under the same lock).

Skipped automatically when the active settings are not the integration layer
(unit job: SQLite per Section 18) or Postgres is unreachable — the skip reason
carries the exact command:

    uv run --directory backend pytest tests/integration --ds apps.core.settings.dev

Every test marks ``transaction=True`` so worker threads see committed rows on
their own connections (``test_claim_race_postgres.py``'s plumbing pattern).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import psycopg
import pytest
from django.conf import settings
from django.db import connection
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from apps.attachments.models import TaskAttachment
from apps.attachments.services import create_attachment
from config.celery import app as celery_app  # noqa: F401 - bind the project app (else shared_task defaults to AMQP)
from tests.attachments.helpers import make_project, make_task

_RUN_COMMAND = "uv run --directory backend pytest tests/integration --ds apps.core.settings.dev"

# Sniffed content per distinct upload; sized well under any cap so only the
# configured limit decides acceptance (the race is about counters, not size).
_PNG_TEMPLATE = b"\x89PNG\r\n\x1a\n" + b"\x00" * 48


def _skip_reason() -> str | None:
    """``None`` when this is the reachable-Postgres integration layer."""
    if "postgresql" not in str(settings.DATABASES["default"]["ENGINE"]):
        return (
            "Section 18 integration layer only: run the Postgres counter race with "
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


# --- shared race plumbing (test_claim_race_postgres.py's pattern) -----------


def _race(
    count: int,
    run: Callable[[int], Any],
    *,
    gate: threading.Semaphore | None = None,
    join_timeout: int = 120,
) -> list[Any]:
    """Run *count* barrier-synchronized workers; return their results.

    Worker exceptions (including the ``ValidationError`` rejections this
    suite expects) are captured by *run* itself; anything else fails the
    test loudly instead of hanging teardown.
    """
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
    for thread in threads:
        thread.join(timeout=join_timeout)
        assert not thread.is_alive(), (
            f"race worker hung ({len(results)} of {count} done, {len(failures)} failures)"
        )
    assert not failures, failures
    assert len(results) == count, (len(results), count)
    return results


def _unique_png(index: int) -> bytes:
    """Distinct sniffable bytes per worker (never a de-dup hit)."""
    return _PNG_TEMPLATE + index.to_bytes(4, "big")


def _upload(task_id: str, data: bytes) -> str:
    """One service-level upload; business rejections answer their code."""
    try:
        outcome = create_attachment(
            task_id=task_id,
            filename="race.png",
            declared_mime="image/png",
            data=data,
            uploaded_by=None,
        )
    except ValidationError as exc:
        codes = {str(key) for key in exc.detail} if isinstance(exc.detail, dict) else set()
        if "file" in codes:
            return "capped"
        raise
    return "duplicate" if outcome.deduplicated else "accepted"


def _media_root(tmp_path: Path) -> override_settings:
    """Isolated local storage for the race (Section 16.3's default backend)."""
    return override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path / "media"))


# --- the count-cap race (MT-1.11-02 risk note) ------------------------------


@pytest.mark.django_db(transaction=True)
def test_concurrent_uploads_never_overshoot_the_count_cap(tmp_path: Path) -> None:
    """Racing distinct uploads stop exactly at ``ATTACHMENT_MAX_PER_TASK``."""
    project = make_project(pid="PID00191")
    task = make_task(project, 1)
    cap = 4

    with _media_root(tmp_path), override_settings(ATTACHMENT_MAX_PER_TASK=cap):
        results = _race(
            16,
            lambda i: _upload(task.pk, _unique_png(i)),
            gate=threading.Semaphore(16),
            join_timeout=180,
        )

        assert results.count("accepted") == cap, results
        assert results.count("capped") == 16 - cap, results
        live = TaskAttachment.objects.filter(task=task, deleted_at__isnull=True)
        assert live.count() == cap, "the count cap must not overshoot under a race"
        # The lock is what makes this true: every accepted row was admitted
        # only after re-reading the counter inside the task row lock.
        assert live.count() <= settings.ATTACHMENT_MAX_PER_TASK


@pytest.mark.django_db(transaction=True)
def test_concurrent_uploads_never_overshoot_the_total_bytes_cap(tmp_path: Path) -> None:
    """The 100 MB total (reduced here) stops the racing byte sum at the cap."""
    project = make_project(pid="PID00192")
    task = make_task(project, 1)
    per_file = len(_unique_png(0))
    cap = per_file * 4  # exactly four uploads fit; the fifth would overshoot

    with (
        _media_root(tmp_path),
        override_settings(
            ATTACHMENT_MAX_TOTAL_BYTES=cap,
            ATTACHMENT_MAX_FILE_BYTES=cap,  # per-file cap is irrelevant here
        ),
    ):
        results = _race(
            12,
            lambda i: _upload(task.pk, _unique_png(i)),
            gate=threading.Semaphore(12),
            join_timeout=180,
        )

        assert results.count("accepted") == 4, results
        total = sum(
            TaskAttachment.objects.filter(task=task, deleted_at__isnull=True).values_list(
                "size_bytes", flat=True
            )
        )
        assert total <= cap, f"total {total} bytes overshoot the {cap}-byte cap"


@pytest.mark.django_db(transaction=True)
def test_concurrent_identical_uploads_de_duplicate_to_one_record(tmp_path: Path) -> None:
    """Many racing uploads of the same bytes collapse to one record (9.5)."""
    project = make_project(pid="PID00193")
    task = make_task(project, 1)
    shared = _unique_png(7)

    with _media_root(tmp_path):
        results = _race(
            12,
            lambda _i: _upload(task.pk, shared),
            gate=threading.Semaphore(12),
            join_timeout=180,
        )

        # Every worker either created the record or mapped onto it — never two.
        assert set(results) <= {"accepted", "duplicate"}, results
        assert results.count("accepted") == 1, results
        assert TaskAttachment.objects.filter(task=task).count() == 1
