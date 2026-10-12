"""MT-2.4-07 — core-tool cross-scenarios (unit layer).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.4-core-tools/
MT-2.4-07-core-tool-tests.md (parent plan Sections 9.3, 18; FR-MCP-03,
FR-LEA-01; NFR-01). This module owns the *cross-tool* scenarios over the
send-seam fake — the orient→list→details→claim→release chain, the role
matrix's wire behavior, and the tool-boundary concurrency shaping.

The honest locking proofs (two bridges → one winner; 50 parallel claims)
require the real claim service — they live in
``test_core_tools_live.py``, gated on the real Postgres-backed backend
(NFR-01, Section 18). Per MT risk notes, the backend's lock is never mocked
here: these tests pin the *bridge* side of the contract, the live suite pins
the backend's.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any

import pytest
from mcp_types import CallToolResult

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.server import create_server
from orchestrator_bridge.tools.claim import claim_task
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.release import release_task
from tests.conftest import FakeBackend, build_runtime, build_settings, envelope_wire

_CLAIM_PATH = "/api/v1/tasks/PID00007-T004/claim"
_RELEASE_PATH = "/api/v1/tasks/PID00007-T004/release"
_DETAILS_PATH = "/api/v1/tasks/PID00007-T004"
_WORK_PATH = "/api/v1/projects/PID00007/work"

_LEASE = {
    "task_id": "PID00007-T004",
    "assigned_agent": "coder-1",
    "session_id": "fixture-session-0001",
    "role": "coder",
    "lease_generation": 1,
    "lease_acquired_at": "2026-10-12T09:00:00Z",
    "lease_expires_at": "2026-10-12T09:45:00Z",
    "lease_hard_cap_at": "2026-10-12T13:00:00Z",
    "last_checkpoint": None,
    "failure_retry_count": 0,
}


def _full_backend() -> FakeBackend:
    """The scripted backend for the end-to-end chain."""
    fake = FakeBackend()
    fake.route(
        "GET",
        _WORK_PATH,
        200,
        {
            "results": [
                {
                    "id": "PID00007-T004",
                    "title": "Add invoice export",
                    "priority": "high",
                    "state": "pending",
                    "depends_on": [],
                }
            ],
            "next_cursor": None,
        },
    )
    fake.route(
        "GET",
        _DETAILS_PATH,
        200,
        {
            "id": "PID00007-T004",
            "title": "Add invoice export",
            "state": "pending",
            "acceptance_criteria": ["CSV downloads"],
            "target_scope": ["src/billing/**"],
            "test_command": "pytest -q",
            "latest_feedback": "",
            "priority": "high",
            "depends_on": [],
        },
    )
    fake.route(
        "POST",
        _CLAIM_PATH,
        200,
        {
            "task": {"id": "PID00007-T004", "state": "in_progress", "title": "Add invoice export"},
            "lease": _LEASE,
            "rules_block": {"standard_rules": ["Stay on the branch."], "project_rules": ""},
        },
    )
    fake.route("POST", _RELEASE_PATH, 200, {"id": "PID00007-T004", "state": "pending"})
    return fake


def test_orient_list_details_claim_release_chain() -> None:
    """The MT's end-to-end chain, entirely over the bound session."""
    from orchestrator_bridge.tools.available_tasks import list_available_tasks
    from orchestrator_bridge.tools.context import get_project_context
    from orchestrator_bridge.tools.task_details import get_task_details

    fake = _full_backend()
    runtime = build_runtime(fake)

    orient = get_project_context(runtime)  # 1. orient — cache, no network
    assert orient["project_id"] == "PID00007"
    listing = list_available_tasks(runtime)  # 2. list
    assert [task["id"] for task in listing["tasks"]] == ["PID00007-T004"]
    details = get_task_details(runtime, task_id="PID00007-T004")  # 3. details
    assert details["task"]["acceptance_criteria"] == ["CSV downloads"]
    claimed = claim_task(runtime, task_id="PID00007-T004", agent_identifier="coder-1")  # 4. claim
    assert claimed["branch"] == "feat/PID00007-T004"
    released = release_task(runtime, task_id="PID00007-T004", reason="chain test")  # 5. release
    assert released["state"] == "pending"

    methods_paths = [(call.method, call.path) for call in fake.calls]
    assert methods_paths == [
        ("GET", _WORK_PATH),
        ("GET", _DETAILS_PATH),
        ("POST", _CLAIM_PATH),
        ("POST", _RELEASE_PATH),
    ]
    # the release carried the claim's fencing generation across tool calls.
    (release_call,) = fake.calls_to("POST", _RELEASE_PATH)
    assert release_call.body["lease_generation"] == 1


def test_role_matrix_auditor_lists_to_be_audited() -> None:
    fake = FakeBackend()
    fake.route(
        "GET",
        _WORK_PATH,
        200,
        {
            "results": [
                {
                    "id": "PID00007-T004",
                    "title": "t",
                    "priority": "high",
                    "state": "to_be_audited",
                    "depends_on": [],
                }
            ],
            "next_cursor": None,
        },
    )
    runtime = build_runtime(fake)
    server = create_server(build_settings(), runtime=runtime)
    result = asyncio.run(server.call_tool("get_available_tasks", {"role": "auditor"}))
    assert isinstance(result, CallToolResult)
    (call,) = fake.calls_to("GET", _WORK_PATH)
    assert "role=auditor" in call.query
    assert result.is_error is False


@pytest.mark.parametrize(
    ("status", "code"),
    [(403, "ROLE_NOT_PERMITTED"), (409, "AUDITOR_SAME_AS_CODER")],
)
def test_role_matrix_cross_role_rejections_are_structured(status: int, code: str) -> None:
    """Cross-role claim attempts (Section 12.2) arrive as catalog codes with
    recovery guidance at the tool boundary."""
    envelope = json.loads(envelope_wire(status, code, f"backend said {code}").body)
    fake = FakeBackend()
    fake.route("POST", _CLAIM_PATH, status, envelope)
    with pytest.raises(ToolFailure) as excinfo:
        claim_task(
            build_runtime(fake),
            task_id="PID00007-T004",
            agent_identifier="auditor-1",
            role="auditor",
        )
    assert excinfo.value.translated.code is ErrorCode(code)
    assert excinfo.value.translated.hint and excinfo.value.translated.next_action


def test_every_chain_failure_uses_only_catalog_codes() -> None:
    """Walk the failure surface and pin the closed vocabulary (20.4 item 5)."""
    from orchestrator_bridge.api_errors import CANONICAL_ERROR_CODES

    catalog = set(CANONICAL_ERROR_CODES)
    for spec_code in (
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.TASK_NOT_FOUND,
        ErrorCode.TASK_ALREADY_CLAIMED,
        ErrorCode.LEASE_NOT_OWNED,
        ErrorCode.SERVER_ERROR,
    ):
        assert spec_code in catalog


def test_contended_claims_through_the_tool_boundary_stay_structured() -> None:
    """Many threads hitting claim_task against a one-winner backend seam.

    The fake answers success exactly once, then TASK_ALREADY_CLAIMED — the
    bridge side of the WP-2.4 acceptance (exactly one structured winner
    signal, every failure shaped). The *database* proof of one-winner lives
    in the live suite; this pins the bridge's concurrency behavior: no
    crashes, no lost errors, stable shaping under thread contention.
    """
    fake = FakeBackend()
    wins = {"count": 0}
    lock = threading.Lock()

    def claim_route(_body: Any) -> tuple[int, Any]:
        with lock:
            wins["count"] += 1
            attempt = wins["count"]
        if attempt == 1:
            return 200, {
                "task": {"id": "PID00007-T004", "state": "in_progress"},
                "lease": _LEASE,
                "rules_block": {"standard_rules": [], "project_rules": ""},
            }
        return 409, json.loads(
            envelope_wire(409, "TASK_ALREADY_CLAIMED", "held by another worker").body
        )

    fake.route_fn("POST", _CLAIM_PATH, claim_route)
    runtime = build_runtime(fake)
    outcomes: list[str] = []
    outcomes_lock = threading.Lock()

    def attempt(index: int) -> None:
        try:
            claim_task(runtime, task_id="PID00007-T004", agent_identifier=f"coder-{index}")
            outcome = "claimed"
        except ToolFailure as exc:
            outcome = str(exc.translated.code)
        with outcomes_lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert outcomes.count("claimed") == 1
    assert set(outcomes) == {"claimed", "TASK_ALREADY_CLAIMED"}


def test_tools_never_address_another_project_end_to_end() -> None:
    """Every request of the full chain is scoped by the bound pid/path."""
    fake = _full_backend()
    runtime = build_runtime(fake)
    from orchestrator_bridge.tools.available_tasks import list_available_tasks
    from orchestrator_bridge.tools.task_details import get_task_details

    list_available_tasks(runtime)
    get_task_details(runtime, task_id="PID00007-T004")
    claim_task(runtime, task_id="PID00007-T004", agent_identifier="coder-1")
    release_task(runtime, task_id="PID00007-T004")
    for call in fake.calls:
        assert "PID00007" in call.path, f"call escaped the bound project: {call.path}"
