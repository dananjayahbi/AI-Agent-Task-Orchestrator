"""Shared plumbing for the WP-3.2 submission suites (MT-3.2-01 … 05).

Not a test module (no ``test_`` prefix), mirroring ``tests/wp15_helpers``
and ``tests/wp16_helpers``. Three concerns every WP-3.2 suite shares:

* **Registry restore (mandatory)** — ``submit_resolution`` calls
  ``ensure_submission_wired()``, which replaces the loader's T7/T8 stubs
  and adds T10's two rows on the process registry. The WP-1.5 suites
  assert those stubs (``SPECS`` snapshots the stub rows at collection
  time) and snapshot/restore per test, so every module that can trigger
  the wiring imports :func:`restore_submission_registry` — each test
  starts and ends on the stub registry, with the policy seam reset to
  its fail-closed default (and ``reset_hooks`` restoring the WP-1.5
  event/push seams the way production runs them).
* **Local storage** — submissions always store a patch artifact (an
  empty patch stores an empty body, not a marker), so every suite that
  reaches the service runs against a per-test ``MEDIA_ROOT`` instead of
  the default ``/media`` (same ``override_settings`` pattern as the
  attachments suites).
* **Fresh throttle budgets** — ``AgentEndpointThrottle`` history is
  process state; the autouse clear keeps every test at full budget.

Fixtures here are *imported* into each suite's namespace (the wp16
promotion trick), so no shared ``conftest.py`` is touched.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.errors import CANONICAL_ERROR_CODES
from apps.projects.models import Project
from apps.tasks.models import Task, TaskState
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY
from apps.tasks.state_machine.transitions_submission import set_policy_decision_hook

from .wp15_helpers import install_event_recorder, install_push_recorder, reset_hooks
from .wp16_helpers import (
    PASSWORD,
    active_policy_project,
    claim,
    make_pending_task,
    make_project,
    make_task,
)

__all__ = [
    "PASSWORD",
    "SAMPLE_BRANCH",
    "SAMPLE_PATCH",
    "SAMPLE_SHA",
    "_code",
    "active_policy_project",
    "agent_client",
    "claim",
    "install_event_recorder",
    "install_push_recorder",
    "issue_agent_token",
    "login_owner",
    "make_pending_task",
    "make_project",
    "make_task",
    "submission_body",
]

# A canonical git-format patch fixture shared by the endpoint suites —
# hand-computed stats (the parser suite keeps its own larger matrix):
# 2 files, 2 insertions (file 1's two "+"), 2 deletions (file 1's one
# "-" plus file 2's one "-").
SAMPLE_PATCH = (
    "diff --git a/src/billing/invoice.py b/src/billing/invoice.py\n"
    "index 1234567..89abcde 100644\n"
    "--- a/src/billing/invoice.py\n"
    "+++ b/src/billing/invoice.py\n"
    "@@ -1,3 +1,4 @@\n"
    " def render():\n"
    '-    return "old"\n'
    '+    return "new"\n'
    "+    return_flags = True\n"
    "     return payload\n"
    "diff --git a/docs/readme.md b/docs/readme.md\n"
    "index aaa1111..bbb2222 100644\n"
    "--- a/docs/readme.md\n"
    "+++ b/docs/readme.md\n"
    "@@ -10,2 +10,1 @@\n"
    " keep-this-line\n"
    "-drop-this-line\n"
)

SAMPLE_BRANCH = "feat/PID00001-T001"
SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret


@pytest.fixture(autouse=True)
def restore_submission_registry() -> Iterator[None]:
    """Snapshot the registry; pin the seam fail-closed; restore both after.

    Autouse in every WP-3.2 module that imports it (each suite's
    namespace picks it up — the same promotion trick wp16 uses). The
    seam is pinned to ``None`` **before** the test as well as after:
    WP-3.4's engine installs itself in ``AuditConfig.ready()``, so an
    ambient engine must never leak into a suite asserting the
    documented fail-closed default (the seam still fails closed the
    moment a fixture removes the hook).
    """
    ensure_registered()
    snapshot = DEFAULT_REGISTRY.specs()
    set_policy_decision_hook(None)
    try:
        yield
    finally:
        DEFAULT_REGISTRY.replace_all(snapshot)
        set_policy_decision_hook(None)
        reset_hooks()


@pytest.fixture(autouse=True)
def local_storage(tmp_path: Path) -> Iterator[None]:
    """Per-test ``MEDIA_ROOT`` so patch storage never touches ``/media``."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — fresh budget per test."""
    cache.clear()
    yield
    cache.clear()


def login_owner(username: str = "owner-wp32") -> APIClient:
    """A logged-in owner session (cookie transport) for token minting.

    Suites wrap this one-line body in their own ``owner_client``
    fixture (the wp16 convention: fixtures live in each suite, the
    helper owns only the shared code — so no module-level fixture name
    collides with a test parameter, F811).
    """
    User.objects.create_user(username, None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


def issue_agent_token(owner_client: APIClient, project_id: str, *scopes: str) -> dict[str, Any]:
    """Mint a project-scoped agent token through the real Owner API."""
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": list(scopes)}
    )
    assert response.status_code == 201, response.content
    return dict(response.json())


def agent_client(token_payload: dict[str, Any]) -> APIClient:
    """A plain client carrying one agent bearer token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_payload['token']}")
    return client


def claimed_task(
    project: Project,
    index: int,
    *,
    session_id: str = "sess_wp32",
    **overrides: Any,
) -> Task:
    """One ``in_progress`` task held by *session_id* (T4 via the real service)."""
    task = make_pending_task(project, index, **overrides)
    claim(task, session_id=session_id)
    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS
    return task


def submission_body(**overrides: Any) -> dict[str, Any]:
    """A valid ``POST /tasks/{id}/resolution`` body for ``sess_wp32``."""
    body: dict[str, Any] = {
        "session_id": "sess_wp32",
        "lease_generation": 1,
        "git_branch": SAMPLE_BRANCH,
        "commit_sha": SAMPLE_SHA,
        "execution_summary": "Implemented the export and ran the suite.",
        "requires_human_attention": False,
        "risk_justification": "",
        "patch": SAMPLE_PATCH,
    }
    body.update(overrides)
    return body


def _code(response: Any) -> str:
    """The catalog code of one standard envelope (five fields, asserted)."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (20.4 item 5)"
    return str(error["code"])
