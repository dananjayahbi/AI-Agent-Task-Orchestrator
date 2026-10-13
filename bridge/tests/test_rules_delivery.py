"""MT-2.7-03 — rules delivered through initialize instructions and claim responses.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.7-rules-injection/
MT-2.7-03-rules-delivery.md (Sections 10.6, 19, 20.4, 20.5; FR-MCP-05; gap
G-08). The initialize response's server instructions carry the coder block
plus appended project rules; every claim response carries a role-appropriate,
parameterized block; both channels draw from the single render path and agree
byte-for-byte for the same session inputs.
"""

from __future__ import annotations

from orchestrator_bridge.rules import render_session_rules
from orchestrator_bridge.server import create_server
from orchestrator_bridge.tools.claim import claim_task
from tests.conftest import FakeBackend, build_runtime, build_settings

_CLAIM_PATH = "/api/v1/tasks/PID00007-T004/claim"

_TASK_ROW = {
    "id": "PID00007-T004",
    "project_id": "PID00007",
    "title": "Add invoice export",
    "state": "in_progress",
    "test_command": "pytest -q tests/billing",
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


def _fake() -> FakeBackend:
    fake = FakeBackend()
    fake.route(
        "POST",
        _CLAIM_PATH,
        200,
        {
            "task": _TASK_ROW,
            "lease": _LEASE,
            "rules_block": {"standard_rules": [], "project_rules": ""},
        },
    )
    return fake


def test_initialize_instructions_contain_the_merged_coder_rules() -> None:
    """G-08 channel one: the MCP server instructions are the coder block."""
    runtime = build_runtime(_fake())
    server = create_server(build_settings(), runtime=runtime)
    instructions = server.instructions
    assert isinstance(instructions, str)
    assert "8. Provide a clear execution summary." in instructions
    assert "Project rule: run the tests." in instructions  # appended project rules
    assert instructions.index("8.") < instructions.index("Project rule:")
    # Connect-time generic phrasing: no task exists yet.
    assert "the branch returned by claim_task" in instructions


def test_unbound_server_advertises_no_instructions() -> None:
    server = create_server(build_settings())
    assert server.instructions is None


def test_claim_response_rules_carry_role_and_parameters() -> None:
    runtime = build_runtime(_fake())
    result = claim_task(runtime, task_id="PID00007-T004", agent_identifier="coder-1")
    text = result["rules"]["text"]
    assert result["rules"]["role"] == "coder"
    assert "pytest -q tests/billing" in text  # the task's own test command
    assert "feat/PID00007-T004" in text  # the claim's branch
    assert "every 15 minutes" in text  # lease-derived (45 // 3)
    assert "Project rule: run the tests." in text


def test_repeated_claims_re_deliver_fresh_lease_derived_intervals() -> None:
    """Each claim renders from its own lease — a shorter lease, a tighter cadence."""
    fake = _fake()
    short_lease = dict(_LEASE, lease_expires_at="2026-10-12T09:15:00Z")
    fake.route(
        "POST",
        _CLAIM_PATH,
        200,
        {
            "task": _TASK_ROW,
            "lease": short_lease,
            "rules_block": {"standard_rules": [], "project_rules": ""},
        },
    )
    runtime = build_runtime(fake)
    result = claim_task(runtime, task_id="PID00007-T004", agent_identifier="coder-1")
    assert "every 5 minutes" in result["rules"]["text"]  # 15 // 3


def test_auditor_claim_gets_the_auditor_obligations() -> None:
    runtime = build_runtime(_fake())
    result = claim_task(
        runtime, task_id="PID00007-T004", agent_identifier="auditor-1", role="auditor"
    )
    text = result["rules"]["text"]
    assert result["rules"]["role"] == "auditor"
    assert "full test and lint matrix" in text
    assert "Report honest confidence" in text
    assert "Work only on the assigned branch" not in text


def test_both_channels_are_byte_identical_for_same_session_inputs() -> None:
    """MT-2.7-03 acceptance: one render path, no divergence between channels.

    The initialize instructions and ``get_project_context`` render
    identically; the claim channel renders through the same function, so the
    only differences are the claim's own parameters (branch, test command,
    lease interval) — asserted by rebuilding the expected text with exactly
    those parameters.
    """
    runtime = build_runtime(_fake())
    server = create_server(build_settings(), runtime=runtime)
    from orchestrator_bridge.tools.context import get_project_context

    context_payload = get_project_context(runtime)
    assert server.instructions == context_payload["rules"]  # byte-identical

    result = claim_task(runtime, task_id="PID00007-T004", agent_identifier="coder-1")
    expected = (
        render_session_rules(  # same session inputs as the other channels…
            "coder",
            project_rules=runtime.context.rules if runtime.context else "",
            policy_summary=runtime.context.policy_summary if runtime.context else {},
        )
        .replace(
            "the branch returned by claim_task (derived from the manifest prefix and the task id)",
            "feat/PID00007-T004",
        )
        .replace("the task's test command (from get_task_details)", "pytest -q tests/billing")
    )
    # …plus the claim's parameters — still the same render source.
    assert result["rules"]["text"] == expected


def test_context_rules_update_on_cache_refresh_after_owner_edit() -> None:
    """Fetch-on-refresh (MT-2.7-02): an edited project rule appears on the
    miss path — the cache serves the refreshed text thereafter."""
    fake = FakeBackend()
    fake.route(
        "GET",
        "/api/v1/projects/PID00007",
        200,
        {"id": "PID00007", "name": "Tea ERP", "system_prompt_rules": "New owner rule."},
    )
    fake.route("GET", "/api/v1/projects/PID00007/policy", 200, {"lease_duration_minutes": 45})
    runtime = build_runtime(fake)
    runtime.context = None  # resumed session: cache missing
    from orchestrator_bridge.tools.context import get_project_context

    first = get_project_context(runtime)
    assert "New owner rule." in first["rules"]
    second = get_project_context(runtime)
    assert second == first  # served from the refreshed cache
    assert len(fake.calls) == 2  # no refetch


def test_project_context_payload_shape_is_unchanged() -> None:
    from orchestrator_bridge.tools.context import get_project_context

    runtime = build_runtime(_fake())
    result = get_project_context(runtime)
    assert set(result) == {"project_id", "project_name", "rules", "policy_summary"}


def test_initialize_instructions_reach_the_wire_over_stdio_handshake() -> None:
    """Wire-level proof lives in the subprocess handshake test.

    ``tests/test_entrypoints.py::test_stdio_process_handshake_lists_core_tools``
    drives a real ``initialize`` over stdio and asserts the response's
    ``instructions`` carry the Section 10.6 coder rules plus the stub
    project's appended rule — the inspector-equivalent evidence recorded in
    the WP changelog. This unit test pins the same content at the seam the
    handshake serializes from.
    """
    runtime = build_runtime(_fake())
    server = create_server(build_settings(), runtime=runtime)
    assert "Coder rules (Section 10.6)" in (server.instructions or "")
