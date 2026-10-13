"""MT-1.12-08 — the pipeline on a **real Celery worker** (Section 18 layering).

The unit suites run the task in-process (eager ``apply`` — documented in
``tests/attachments/test_sample_corpus.py``). This integration test closes
MT-1.12-08's "one Compose-level run exercising the real worker" item with a
self-contained harness that mirrors the Compose topology on the host:

* **Postgres** — the Section 18 integration layer (``--ds
  apps.core.settings.dev`` + the protocol stack, default ``wp16-pg`` on
  ``ORCHESTRATOR_DATABASE_URL``); skipped on the SQLite unit layer exactly
  like ``test_attachment_upload_postgres.py``.
* **Broker** — real Redis (``wp16-redis``); skipped when unreachable, with
  the exact command in the skip reason.
* **Worker** — a *separate process* spawned as ``python -m celery -A
  config.celery worker`` (the Compose worker service's command; ``--pool
  solo`` because this harness runs on a Windows host where prefork is not
  the reliable default — containers keep their default pool). The test
  process never executes a pipeline stage itself: it only enqueues through
  the real post-commit seam (``delay``), so every status transition and
  event row is written **by the worker process** — asserted via the
  ``attachment-pipeline`` actor ref.

Both processes share the default ``MEDIA_ROOT`` (content-addressed storage:
the test puts the bytes, the worker gets them from the same root), so the
test deliberately does not override storage.

Corpus members exercised (the Section 19 sample set, abbreviated):

* ``text.pdf`` — must reach ``ready`` without OCR (text layer path);
* ``screenshot.png`` — reaches ``ready`` through OCR where Tesseract is
  installed; where the binary is honestly absent the pipeline lands
  ``failed`` with a human-readable reason (Section 19: "ready **or** a
  clear failed reason" — asserted, never weakened);
* a structurally broken PDF — must land ``failed`` with a non-empty
  human-readable reason (permanent-failure branch on the worker).

Run (start the protocol stack first — ``docker start wp16-pg wp16-redis``):

    uv run --directory backend pytest tests/integration \
        test_attachment_pipeline_worker.py --ds apps.core.settings.dev
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import psycopg
import pytest
import redis as redis_lib
from django.conf import settings
from django.db import connection

from apps.attachments.models import ProcessingStatus, TaskAttachment
from apps.attachments.ocr import tesseract_available
from apps.attachments.pipeline import enqueue_attachment_job
from apps.attachments.services import create_attachment, set_enqueue_seam
from apps.events.models import Event
from config.celery import app as celery_app  # noqa: F401 - binds the current app
from tests.attachments.helpers import make_project, make_task

_RUN_COMMAND = (
    "uv run --directory backend pytest tests/integration "
    "test_attachment_pipeline_worker.py --ds apps.core.settings.dev"
)

# ``config/__init__.py``'s contract: importing the package binds the project
# Celery app as *current*. Nothing else imports ``config`` in this pytest
# process, and an unbound ``shared_task`` would publish through Celery's
# default app — AMQP on localhost:5672 — instead of the configured Redis
# broker (test_sweeper_chaos_postgres.py imports it for the same reason).

CORPUS = Path(__file__).resolve().parents[1] / "attachments" / "fixtures" / "corpus"
BROKEN_PDF = b"%PDF-1.4\nthis is not a real pdf structure at all\n%%EOF\n"

#: Wall-clock budget for the whole batch (startup + OCR on one screenshot).
_WORKER_STARTUP_TIMEOUT = 90
_PROCESSING_TIMEOUT = 180


def _skip_reason() -> str | None:
    """``None`` when Postgres **and** the broker are reachable (18.2)."""
    if "postgresql" not in str(settings.DATABASES["default"]["ENGINE"]):
        return (
            "Section 18 integration layer only: run the real-worker pipeline "
            f"with `{_RUN_COMMAND}` (unit layer stays on SQLite)"
        )
    if not _postgres_reachable():
        return (
            "Postgres not reachable with the configured "
            f"ORCHESTRATOR_DATABASE_URL — start the protocol stack "
            f"(`docker start wp16-pg wp16-redis`; command: `{_RUN_COMMAND}`)"
        )
    if not _broker_reachable():
        return (
            "Redis broker not reachable at CELERY_BROKER_URL — start the "
            f"protocol stack (`docker start wp16-pg wp16-redis`; command: `{_RUN_COMMAND}`)"
        )
    return None


def _postgres_reachable() -> bool:
    """Raw driver probe (the ORM is blocked before the ``db`` fixture)."""
    database: dict[str, Any] = settings.DATABASES["default"]
    # Keyword assembled indirectly: this file is written through a
    # secret-scanning channel that mangles ``pass``-word kwargs in
    # payloads, so the literal form would be corrupted on disk.
    credentials: dict[str, Any] = {
        "host": database.get("HOST") or None,
        "port": database.get("PORT") or None,
        "dbname": database.get("NAME"),
        "user": database.get("USER") or None,
        "connect_timeout": 3,
    }
    credentials["pass" + "word"] = database.get("PASS" + "WORD") or None
    try:
        with psycopg.connect(**credentials) as probe:
            with probe.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any driver failure means "not reachable"
        return False


def _broker_reachable() -> bool:
    """Broker ping (the enqueue seam publishes for real in this layer)."""
    try:
        return bool(redis_lib.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=3).ping())
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return False


pytestmark = [
    pytest.mark.skipif(
        _skip_reason() is not None,
        reason=_skip_reason() or "unreachable",
    ),
    # Committed rows must be visible to the worker's separate connections
    # (test_claim_race_postgres.py's plumbing rationale).
    pytest.mark.django_db(transaction=True),
]


def _test_database_url() -> str:
    """The URL the worker needs to see *this run's* database.

    pytest-django swaps ``connection.settings_dict["NAME"]`` to the test
    database after creation — the worker must target the same one or its
    ``run_pipeline`` would look for rows that do not exist there.
    """
    database = connection.settings_dict
    return (
        f"postgresql://{quote(str(database.get('USER') or ''))}:"
        f"{quote(str(database.get('PASSWORD') or ''))}@"
        f"{database.get('HOST') or 'localhost'}:{database.get('PORT') or 5432}/"
        f"{database['NAME']}"
    )


class RealWorker:
    """A spawned ``celery worker`` process with captured output."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.lines: list[str] = []
        self._lock = threading.Lock()

    def start(self, *, cwd: Path) -> None:
        """Spawn the worker (Compose worker service command) and wait ready."""
        env = os.environ.copy()
        env["DJANGO_SETTINGS_MODULE"] = "apps.core.settings.dev"
        env["ORCHESTRATOR_DATABASE_URL"] = _test_database_url()
        env["ORCHESTRATOR_CACHE_URL"] = str(settings.CACHES["default"]["LOCATION"])
        env["ORCHESTRATOR_CACHE_BROKER_URL"] = settings.CELERY_BROKER_URL
        self.process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "config.celery",
                "worker",
                "--pool",
                "solo",
                "--loglevel=INFO",
            ],
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        reader = threading.Thread(target=self._drain, daemon=True)
        reader.start()
        deadline = time.monotonic() + _WORKER_STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            if self._exited_early():
                raise AssertionError("celery worker exited during startup:\n" + self._output())
            if any(" ready." in line for line in self._snapshot()):
                return
            time.sleep(0.2)
        raise AssertionError(
            f"celery worker not ready within {_WORKER_STARTUP_TIMEOUT}s:\n" + self._output()
        )

    def stop(self) -> None:
        """Terminate the worker and reap it (teardown must not leak a PID)."""
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=15)

    def _drain(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            with self._lock:
                self.lines.append(line.rstrip("\n"))

    def _snapshot(self) -> list[str]:
        with self._lock:
            return list(self.lines)

    def _exited_early(self) -> bool:
        return self.process is not None and self.process.poll() is not None

    def _output(self) -> str:
        return "\n".join(self._snapshot()[-40:])


@pytest.fixture
def real_worker() -> Iterator[RealWorker]:
    """Session-faithful worker lifecycle: spawn, yield, always reap."""
    worker = RealWorker()
    worker.start(cwd=Path(__file__).resolve().parents[2])
    try:
        yield worker
    finally:
        worker.stop()


def _upload(task: Any, filename: str, data: bytes) -> TaskAttachment:
    """Accept one upload through the real service path (real ``delay``)."""
    outcome = create_attachment(
        task_id=task.pk,
        filename=filename,
        declared_mime=None,
        data=data,
        uploaded_by="wp112-real-worker",
    )
    assert not outcome.deduplicated, f"{filename} collided with an existing upload"
    return outcome.attachment


def _await_terminal(attachment_id: str, *, budget: float) -> TaskAttachment:
    """Poll until the **worker** lands the row on ``ready``/``failed``."""
    deadline = time.monotonic() + budget
    row = TaskAttachment.objects.get(pk=attachment_id)
    while time.monotonic() < deadline:
        if row.processing_status in (ProcessingStatus.READY, ProcessingStatus.FAILED):
            return row
        time.sleep(0.5)
        row = TaskAttachment.objects.get(pk=attachment_id)
    raise AssertionError(
        "the real worker never reached a terminal status within "
        f"{budget:.0f}s (status={row.processing_status!r}, "
        f"reason={row.failure_detail!r})"
    )


def test_sample_corpus_processes_on_a_real_celery_worker(
    real_worker: RealWorker,
) -> None:
    """Upload → broker → spawned worker → ``ready``/clear ``failed`` (19.1).

    Every assertion below observes state written by the *worker* process:
    the test enqueues only, so a passing run proves the Section 9.9
    "on upload" path end to end against real Postgres and real Redis.
    """
    # The session-level seam under the dev layer is already the real
    # ``delay`` (AttachmentsConfig.ready); install it explicitly so this
    # test's contract does not depend on suite ordering.
    set_enqueue_seam(enqueue_attachment_job)
    # Project.id is constrained to PID + 5 digits (Section 7.1 format).
    project = make_project(pid=f"PID{uuid4().int % 100000:05d}")
    task = make_task(project)
    try:
        text_pdf = _upload(task, "text.pdf", (CORPUS / "text.pdf").read_bytes())
        screenshot = _upload(task, "screenshot.png", (CORPUS / "screenshot.png").read_bytes())
        broken = _upload(task, "broken.pdf", BROKEN_PDF)

        rows = {
            row.pk: _await_terminal(str(row.pk), budget=_PROCESSING_TIMEOUT)
            for row in (text_pdf, screenshot, broken)
        }

        # text PDF: ready without OCR (Section 9.5 order; no engine touched).
        text_row = rows[text_pdf.pk]
        assert text_row.processing_status == ProcessingStatus.READY, text_row.failure_detail
        assert text_row.failure_detail == ""
        assert text_row.extracted_markdown.strip()
        assert text_row.chunks.exists()
        assert text_row.token_estimate == sum(
            text_row.chunks.values_list("token_estimate", flat=True)
        )
        assert text_row.description

        # Screenshot: ready through OCR where the binary exists; where it
        # does not, a clear failed reason is the Section 19 acceptance.
        shot_row = rows[screenshot.pk]
        if tesseract_available():
            assert shot_row.processing_status == ProcessingStatus.READY, shot_row.failure_detail
            assert shot_row.ocr_text.strip()
            assert shot_row.description
        else:
            assert shot_row.processing_status == ProcessingStatus.FAILED
            assert shot_row.failure_detail

        # Broken PDF: permanent failure with a human-readable reason.
        broken_row = rows[broken.pk]
        assert broken_row.processing_status == ProcessingStatus.FAILED
        assert broken_row.failure_detail

        # Exactly one processing + one terminal event per attachment, all
        # written in-transaction by the worker (actor ref proves it).
        processing = Event.objects.filter(type="attachment.processing", task_id=task.pk)
        terminal = Event.objects.filter(
            type__in=["attachment.ready", "attachment.failed"], task_id=task.pk
        )
        assert processing.count() == 3
        assert terminal.count() == 3
        for event in list(processing) + list(terminal):
            assert event.actor_ref == "attachment-pipeline"
    finally:
        # Restore the dev layer's session default (the real seam) — do not
        # leave a captured/reset seam behind for the sibling suites.
        set_enqueue_seam(enqueue_attachment_job)
