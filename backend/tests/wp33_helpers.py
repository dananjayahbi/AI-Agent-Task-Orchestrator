"""Shared plumbing for the WP-3.3 audit suites (MT-3.3-01 … 05).

Not a test module (no ``test_`` prefix), mirroring ``tests/wp15_helpers.py``
and ``tests/wp16_helpers.py``: the registry/hook restore fixture every
WP-3.3 suite must autouse, credential helpers over the real Owner API,
and the auditor-flow seeds (an ``to_be_audited`` task carrying its
current-attempt ``TaskResolution`` — the independence inputs).

**Why the restore fixture is mandatory** (the WP-1.6 rule, restated):
``claim_task``/the verdict service/sweeper call ``ensure_wired()``,
``ensure_submission_wired()`` and ``ensure_audit_wired()``, which
replace or add rows on the process registry — the WP-1.5 suites assert
the loader's stub rows (``SPECS`` snapshots them at collection time) and
snapshot/restore per test. Every module that can trigger any wiring
therefore imports :func:`restore_audit_registry`, which additionally
resets the WP-3.4 decision hook so an approving engine installed by one
test never leaks into the next (the fail-closed default must be the
ambient state).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.agents.models import AgentSession
from apps.projects.models import Project
from apps.tasks.models import Task, TaskResolution, TaskState
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY

from .wp15_helpers import (  # noqa: F401  (re-exported for suites)
    install_event_recorder,
    make_project,
    make_task,
    registered_registry,
    reset_hooks,
)
from .wp16_helpers import active_policy_project, make_pending_task, restore_lease_registry

__all__ = [
    "PASSWORD",
    "JsonAPIClient",
    "active_policy_project",
    "agent_client",
    "auditable_task",
    "auditor_claim_body",
    "claim_as_auditor",
    "clean_throttle_cache",
    "install_event_recorder",
    "issue_agent_token",
    "make_pending_task",
    "login_owner_client",
    "make_project",
    "make_task",
    "owner_client",
    "register_session",
    "reset_hooks",
    "restore_audit_registry",
    "restore_lease_registry",
    "verdict_body",
]

PASSWORD = "wp33-tests-1!"  # pragma: allowlist secret


class JsonAPIClient(APIClient):
    """An ``APIClient`` whose POST bodies are JSON by default.

    DRF's test client defaults to multipart, which refuses nested dict
    values — the Section 10.5 verdict payload (``evidence``) needs
    ``format="json"`` (the WP-3.2 suites pass it per call; this suite
    sets it once).
    """

    default_format = "json"


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — keep every test's budgets fresh."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def restore_audit_registry() -> Iterator[None]:
    """Snapshot the registry + hooks; restore stubs and the fail-closed seam.

    Autouse in every WP-3.3 module that imports it (each suite's
    namespace picks it up — the same promotion trick wp16 uses).
    """
    from apps.audit.decision import set_audit_decision_hook

    ensure_registered()
    snapshot = DEFAULT_REGISTRY.specs()
    try:
        yield
    finally:
        DEFAULT_REGISTRY.replace_all(snapshot)
        reset_hooks()
        set_audit_decision_hook(None)  # fail-closed default must be ambient


def login_owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per caller.

    Suites import *this* and expose their own one-line ``owner_client``
    fixture — pytest injects fixtures from the test module's namespace,
    and importing the fixture itself would make every test parameter an
    F811 redefinition of an unused import.
    """
    User.objects.create_user("owner-wp33", None, PASSWORD)
    api = JsonAPIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner-wp33", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    return login_owner_client()


def issue_agent_token(owner_client: APIClient, project_id: str, *scopes: str) -> dict[str, Any]:
    """Mint a project-scoped agent token through the real Owner API."""
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": list(scopes)}
    )
    assert response.status_code == 201, response.content
    payload: dict[str, Any] = response.json()
    return payload


def agent_client(token_payload: dict[str, Any]) -> JsonAPIClient:
    """A plain client carrying one agent bearer token."""
    client = JsonAPIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_payload['token']}")
    return client


def register_session(project: Project, session_id: str, label: str) -> AgentSession:
    """The Section 7.2 AgentSession row the label half of G-20 reads."""
    return AgentSession.objects.create(
        id=session_id,
        project=project,
        token_id=1,  # fixture token pk — the label lookup never reads it
        agent_label=label,
        transport="stdio",
    )


def auditable_task(
    project: Project,
    index: int,
    *,
    coder_session: str = "sess_wp33_coder",
    coder_label: str | None = None,
    attempt: int = 1,
) -> Task:
    """A ``to_be_audited`` task carrying its current-attempt resolution.

    The direct-row seed T7's outcome would produce: ``attempt_number``
    matches the resolution (the T13/T14 structural guard's contract) and
    ``submitted_by_session`` is the identity MT-3.3-02 compares against.
    ``coder_label`` additionally registers an AgentSession row so the
    label half of the check has its input (omit it for session-only
    fixtures — the recorded skip-if-absent reading).
    """
    task = make_task(
        project,
        index,
        state=TaskState.TO_BE_AUDITED,
        attempt_number=attempt,
        audit_required=True,
    )
    TaskResolution.objects.create(
        task=task,
        attempt_number=attempt,
        branch_name=f"feat/{project.pk}-T{index:03d}",
        commit_sha="0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        execution_summary="wp33 seed submission",
        submitted_by_session=coder_session,
    )
    if coder_label is not None:
        register_session(project, coder_session, coder_label)
    return task


def auditor_claim_body(
    session_id: str = "sess_wp33_auditor", label: str = "wp33-auditor", **extra: Any
) -> dict[str, Any]:
    """The ClaimRequest body carrying the Section 10.5 role=auditor intent."""
    return {
        "session_id": session_id,
        "worker_agent_id": label,
        "role": "auditor",
        **extra,
    }


def claim_as_auditor(
    client: APIClient,
    task_id: str,
    session_id: str = "sess_wp33_auditor",
    label: str = "wp33-auditor",
) -> Any:
    """One auditor claim through the real route (the T11 path)."""
    return client.post(
        f"/api/v1/tasks/{task_id}/claim",
        auditor_claim_body(session_id=session_id, label=label),
    )


def verdict_body(
    task_id: str,
    *,
    session_id: str = "sess_wp33_auditor",
    lease_generation: int = 1,
    verdict: str = "pass",
    confidence: int = 4,
    notes: str = "wp33 audit notes",
    evidence: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """The Section 10.5 verdict payload (evidence defaults to one command)."""
    return {
        "session_id": session_id,
        "lease_generation": lease_generation,
        "task_id": task_id,
        "verdict": verdict,
        "confidence": confidence,
        "notes": notes,
        "evidence": evidence
        if evidence is not None
        else {
            "commands": [
                {"label": "tests", "command": "pytest -q", "exit_code": 0, "summary": "all green"}
            ],
            "lint_clean": True,
        },
        **extra,
    }
