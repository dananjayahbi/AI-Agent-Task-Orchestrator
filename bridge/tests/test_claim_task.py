"""MT-2.4-04 — claim_task returning lease, rules block, branch name.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.4-core-tools/
MT-2.4-04-claim-task.md (parent plan Sections 9.2, 9.3, 10.5, 10.6; FR-MCP-03,
FR-LEA-01; G-09). The former forward note ("WP-2.7 merges at MT-2.7-03") is
resolved: the delivered ``rules`` block is now the bridge's own Section 10.6
render — coder/auditor template + the session's cached project rules, with
this claim's branch, test command and lease-derived checkpoint interval
(MT-2.7-03). The backend's wire ``rules_block`` stays shape-checked.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.manifest import StartupBinding
from orchestrator_bridge.tools.claim import branch_name_for, claim_task
from orchestrator_bridge.tools.errors import ToolFailure
from tests.conftest import (
    MINIMAL_MANIFEST,
    FakeBackend,
    build_runtime,
    envelope_wire,
)

_CLAIM_PATH = endpoint("claim").path.format(id="PID00007-T004")

_TASK_ROW = {
    "id": "PID00007-T004",
    "project_id": "PID00007",
    "title": "Add invoice export",
    "state": "in_progress",
    "priority": "medium",
}
_LEASE = {
    "task_id": "PID00007-T004",
    "assigned_agent": "coder-1",
    "session_id": "fixture-session-0001",
    "role": "coder",
    "lease_generation": 3,
    "lease_acquired_at": "2026-10-12T09:00:00Z",
    "lease_expires_at": "2026-10-12T09:45:00Z",
    "lease_hard_cap_at": "2026-10-12T13:00:00Z",
    "last_checkpoint": None,
    "failure_retry_count": 0,
}
_RULES = {
    "standard_rules": ["Stay on the assigned branch.", "Run the test command."],
    "project_rules": "Keep the ERP invoices deterministic.",
}


def _backend(status: int = 200, payload: Any = None) -> tuple[FakeBackend, dict[str, Any]]:
    body = (
        payload
        if payload is not None
        else {"task": _TASK_ROW, "lease": _LEASE, "rules_block": _RULES}
    )
    fake = FakeBackend()
    fake.route("POST", _CLAIM_PATH, status, body)
    return fake, body


def test_successful_claim_returns_the_three_section_10_5_artifacts() -> None:
    fake, _ = _backend()
    runtime = build_runtime(fake)
    result = claim_task(runtime, task_id="PID00007-T004", agent_identifier="coder-1")
    assert result["branch"] == "feat/PID00007-T004"  # G-09
    assert result["lease"]["generation"] == 3
    assert result["lease"]["expires_at"] == "2026-10-12T09:45:00Z"
    assert result["task"]["id"] == "PID00007-T004"
    assert result["task_id"] == "PID00007-T004"


def test_claim_rules_block_is_the_bridge_section_10_6_render() -> None:
    """MT-2.7-03: the response carries the bridge's render, not the raw block.

    All eight coder rules, the claim's G-09 branch, the lease-derived
    checkpoint interval (45-minute lease → 15), and the session's cached
    project rules appended after the standard rules (Section 10.6 order).
    """
    fake, _ = _backend()
    runtime = build_runtime(fake)
    result = claim_task(runtime, task_id="PID00007-T004", agent_identifier="coder-1")
    rules = result["rules"]
    assert rules["role"] == "coder"
    text = rules["text"]
    assert "8. Provide a clear execution summary." in text
    assert "feat/PID00007-T004" in text  # G-09 branch in rule 1
    assert "every 15 minutes" in text  # 45-minute lease → 15 (RISK-02)
    # The cached fixture project rule is appended, after the standard rules.
    assert "Project rule: run the tests." in text
    assert text.index("8.") < text.index("Project rule:")


def test_wire_body_is_the_claim_request_contract_only() -> None:
    fake, _ = _backend()
    claim_task(build_runtime(fake), task_id="PID00007-T004", agent_identifier="coder-1")
    (call,) = fake.calls_to("POST", _CLAIM_PATH)
    # Exactly the backend's ClaimRequest — no role field (token scopes decide
    # per Section 12.2), no project_id (Section 10.3).
    assert set(call.body) == {"session_id", "worker_agent_id"}
    assert call.body["session_id"] == "fixture-session-0001"
    assert call.body["worker_agent_id"] == "coder-1"
    assert call.headers["Idempotency-Key"]  # NFR-12 / ADR-012


def test_lease_generation_is_recorded_for_the_release_fencing_pair() -> None:
    fake, _ = _backend()
    runtime = build_runtime(fake)
    claim_task(runtime, task_id="PID00007-T004", agent_identifier="coder-1")
    assert runtime.lease_generation("PID00007-T004") == 3


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (409, "TASK_ALREADY_CLAIMED"),
        (409, "CONCURRENCY_LIMIT_REACHED"),
        (409, "DEPENDENCY_UNMET"),
        (409, "AUDITOR_SAME_AS_CODER"),
        (404, "TASK_NOT_FOUND"),
        (403, "ROLE_NOT_PERMITTED"),
    ],
)
def test_named_claim_errors_surface_with_exact_codes_and_guidance(status: int, code: str) -> None:
    envelope = json.loads(envelope_wire(status, code, f"backend said {code}").body)
    fake, _ = _backend(status, envelope)
    with pytest.raises(ToolFailure) as excinfo:
        claim_task(build_runtime(fake), task_id="PID00007-T004", agent_identifier="coder-1")
    translated = excinfo.value.translated
    assert translated.code is ErrorCode(code)
    assert translated.hint and translated.next_action
    if code == "TASK_ALREADY_CLAIMED":
        assert "get_available_tasks" in translated.next_action  # Section 10.5 wording


def test_malformed_claim_response_is_a_structured_server_error() -> None:
    fake, _ = _backend(payload={"task": _TASK_ROW})  # lease/rules missing
    with pytest.raises(ToolFailure) as excinfo:
        claim_task(build_runtime(fake), task_id="PID00007-T004", agent_identifier="coder-1")
    assert excinfo.value.translated.code is ErrorCode.SERVER_ERROR


# --- branch derivation (G-09; WP-2.10 will own and extend) ----------------------


def test_branch_name_is_prefix_plus_task_index() -> None:
    binding = StartupBinding(manifest_path=Path("o.json"), manifest=dict(MINIMAL_MANIFEST))
    assert branch_name_for(binding, "PID00007-T004") == "feat/PID00007-T004"


def test_branch_name_survives_a_malformed_id_without_fabrication() -> None:
    binding = StartupBinding(manifest_path=Path("o.json"), manifest=dict(MINIMAL_MANIFEST))
    assert branch_name_for(binding, "weird") == "feat/PID00007-weird"
