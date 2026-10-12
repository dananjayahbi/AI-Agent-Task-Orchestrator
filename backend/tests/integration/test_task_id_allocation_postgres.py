"""MT-1.4-02 — the 100-concurrent-creations acceptance on **real Postgres**.

Section 18's concurrency layer prescribes "real Postgres, multiple
connections"; this is the Postgres twin of
``tests/test_task_id_allocation.py::test_one_hundred_concurrent_creations_yield_unique_ids``
— same helper, same assertions (100 unique, FR-TSK-01-valid ids for one
project), now over the ``UPDATE ... RETURNING`` row lock that only a
locking backend exercises (the SQLite unit layer substitutes its
single-writer table lock).

Skipped automatically when the active settings are not the integration
layer (unit job: SQLite per Section 18) or Postgres is unreachable —
the skip reason carries the exact command:

    uv run --directory backend pytest tests/integration --ds apps.core.settings.dev

Run with that command against CI's provisioned services (the
``integration-tests`` job) or a local Compose stack.
"""

from __future__ import annotations

import threading
from typing import Any

import psycopg
import pytest
from django.conf import settings

from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task
from apps.tasks.services.ids import is_valid_task_id
from tests.test_task_id_allocation import create_task_concurrently

_RUN_COMMAND = "uv run --directory backend pytest tests/integration --ds apps.core.settings.dev"


def _skip_reason() -> str | None:
    """``None`` when this is the reachable-Postgres integration layer."""
    if "postgresql" not in str(settings.DATABASES["default"]["ENGINE"]):
        return (
            "Section 18 integration layer only: run the Postgres twin with "
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
        ) as connection:
            with connection.cursor() as cursor:
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


@pytest.mark.django_db(transaction=True)
def test_one_hundred_concurrent_creations_yield_unique_ids_on_postgres() -> None:
    """WP-1.4 acceptance on the real backend: 100 parallel, unique ids.

    A semaphore gates simultaneously open sessions well under the stock
    ``max_connections=100`` (100 threads still start together at the
    barrier — the gate only bounds live Postgres sessions). The exact
    counter check additionally proves the transactional semantics: every
    failed create refunded its increment, every committed one consumed
    exactly one number (``task_counter == 100`` for 100 rows).
    """
    project = Project.objects.create(
        id="PID00079",
        name="Postgres concurrent task creations",
        repo_path="/srv/repos/pg-concurrent-tasks",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    gate = threading.Semaphore(40)  # headroom under max_connections=100

    ids = create_task_concurrently(project.pk, threads=100, gate=gate, join_timeout=180)

    assert len(ids) == 100, len(ids)
    assert len(set(ids)) == 100, "a task id was reused"
    for task_id in ids:
        assert is_valid_task_id(task_id), task_id
        assert task_id.startswith("PID00079-"), task_id

    project.refresh_from_db()
    assert project.task_counter == 100, (
        "the counter must advance exactly once per committed creation "
        "(rolled-back attempts refund — FR-TSK-01 gap tolerance)"
    )
    assert Task.objects.filter(project=project).count() == 100
