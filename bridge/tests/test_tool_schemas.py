"""MT-2.4-01 — deterministic schemas for the registered tools (WP-2.6 extends).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.4-core-tools/
MT-2.4-01-core-tool-schemas.md (parent plan Sections 10.3, 10.5, 18, 20.4,
20.5; FR-MCP-03, NFR-11), extended by WP-2.6/MT-2.6-01 and MT-2.6-04
(``log_task_checkpoint`` and ``submit_task_resolution`` enter the catalog
between ``claim_task`` and ``release_task`` — the Section 10.5 order).

Pins the public contract against the Section 10.5 tool catalog table: exact
names, no ``project_id`` anywhere, closed error vocabulary, strict validation
with structured ``VALIDATION_ERROR`` failures, and the wire schemas the MCP
server advertises (``list_tools``) byte-identical to the declared ones.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.server import create_server
from orchestrator_bridge.tools import TOOLS
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.runtime import ToolRuntime
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES, TOOL_SPECS, ToolSpec
from orchestrator_bridge.tools.validation import validate_tool_input
from tests.conftest import build_settings

_VALID_FIXTURES: dict[str, dict[str, Any]] = {
    "get_available_tasks": {},
    "get_task_details": {"task_id": "PID00007-T004"},
    "claim_task": {"task_id": "PID00007-T004", "agent_identifier": "coder-1"},
    "read_task_attachment": {"task_id": "PID00007-T004", "attachment_id": "att-0001"},
    "log_task_checkpoint": {"task_id": "PID00007-T004", "message": "halfway", "percentage": 50},
    "submit_task_resolution": {
        "task_id": "PID00007-T004",
        "git_branch": "feat/PID00007-T004",
        "commit_sha": "a" * 40,
        "execution_summary": "Ran the tests; all green.",
    },
    "release_task": {"task_id": "PID00007-T004", "reason": "scope expansion needed"},
    "submit_audit_verdict": {
        "task_id": "PID00007-T004",
        "verdict": "pass",
        "confidence": 4,
        "evidence": {
            "commands": [
                {"label": "tests", "command": "uv run pytest -q", "exit_code": 0},
            ],
            "lint_clean": True,
        },
        "acceptance_criteria_results": [{"criterion": "Export runs green", "met": True}],
    },
    "get_project_context": {},
}


def _spec(name: str) -> ToolSpec:
    return TOOLS[name]


# --- the catalog itself (Section 10.5 line by line) -----------------------------


def test_exact_tools_in_plan_catalog_order() -> None:
    assert CORE_TOOL_NAMES == (
        "get_available_tasks",
        "get_task_details",
        "claim_task",
        "read_task_attachment",
        "log_task_checkpoint",
        "submit_task_resolution",
        "release_task",
        "submit_audit_verdict",
        "get_project_context",
    )


def test_key_inputs_match_the_section_10_5_table() -> None:
    properties = {name: set(spec.input_schema["properties"]) for name, spec in TOOLS.items()}
    assert properties["get_available_tasks"] == {"priority_filter", "limit", "role"}
    assert properties["get_task_details"] == {"task_id"}
    assert properties["claim_task"] == {"task_id", "agent_identifier", "role"}
    assert properties["read_task_attachment"] == {
        "task_id",
        "attachment_id",
        "format_preference",
        "page_number",
        "force",
    }
    assert properties["log_task_checkpoint"] == {"task_id", "message", "percentage"}
    assert properties["submit_task_resolution"] == {
        "task_id",
        "git_branch",
        "commit_sha",
        "execution_summary",
        "requires_human_attention",
        "risk_justification",
    }
    assert properties["release_task"] == {"task_id", "reason"}
    assert properties["submit_audit_verdict"] == {
        "task_id",
        "verdict",
        "confidence",
        "notes",
        "evidence",
        "acceptance_criteria_results",
    }
    assert properties["get_project_context"] == set()


def test_role_defaults_to_coder_everywhere_it_exists() -> None:
    for name in ("get_available_tasks", "claim_task"):
        role = TOOLS[name].input_schema["properties"]["role"]
        assert role["default"] == "coder"
        assert role["enum"] == ["coder", "auditor"]


def test_no_tool_schema_exposes_a_project_id_parameter() -> None:
    """Section 10.3/10.5 binding rule — the MT's named guard test."""

    def names(value: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for key, item in value.items():
                found.add(str(key))
                found |= names(item)
        elif isinstance(value, list):
            for item in value:
                found |= names(item)
        return found

    for spec in TOOL_SPECS:
        property_names = names(spec.input_schema.get("properties", {}))
        assert "project_id" not in property_names, f"{spec.name} exposes project_id"


def test_every_declared_error_code_is_in_the_section_9_2_catalog() -> None:
    for spec in TOOL_SPECS:
        for code in spec.errors:
            assert isinstance(code, ErrorCode), f"{spec.name}: {code} not in catalog"


def test_claim_declares_the_four_named_plan_errors() -> None:
    declared = set(TOOLS["claim_task"].errors)
    assert {
        ErrorCode.TASK_ALREADY_CLAIMED,
        ErrorCode.CONCURRENCY_LIMIT_REACHED,
        ErrorCode.DEPENDENCY_UNMET,
        ErrorCode.AUDITOR_SAME_AS_CODER,
    } <= declared


def test_strict_schemas_reject_unknown_properties() -> None:
    for spec in TOOL_SPECS:
        assert spec.input_schema.get("additionalProperties") is False


# --- validation layer (FR-MCP-03 deterministic acceptance) ----------------------


def test_valid_fixtures_pass_for_every_tool() -> None:
    for name, fixture in _VALID_FIXTURES.items():
        assert validate_tool_input(_spec(name), dict(fixture)) == fixture


def test_none_arguments_normalize_to_empty_object() -> None:
    # Only the tools with no required inputs accept absent/null arguments;
    # the required-argument tools fail with VALIDATION_ERROR instead.
    for name in ("get_available_tasks", "get_project_context"):
        assert validate_tool_input(_spec(name), None) == {}
    for name in (
        "get_task_details",
        "claim_task",
        "log_task_checkpoint",
        "submit_task_resolution",
        "release_task",
    ):
        with pytest.raises(ToolFailure):
            validate_tool_input(_spec(name), None)


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("get_available_tasks", {"role": "owner"}),
        ("get_available_tasks", {"priority_filter": "now"}),
        ("get_available_tasks", {"limit": 0}),
        ("get_available_tasks", {"limit": 101}),
        ("get_available_tasks", {"limit": "10"}),
        ("get_task_details", {}),
        ("get_task_details", {"task_id": 42}),
        ("claim_task", {"task_id": "PID00007-T004"}),
        ("log_task_checkpoint", {}),
        ("log_task_checkpoint", {"task_id": "PID00007-T004", "percentage": 101}),
        ("log_task_checkpoint", {"task_id": "PID00007-T004", "percentage": -1}),
        ("submit_task_resolution", {"task_id": "PID00007-T004"}),
        ("submit_task_resolution", {"task_id": "PID00007-T004", "commit_sha": "abc"}),
        ("release_task", {}),
        ("get_project_context", {"project_id": "PID00007"}),
        ("get_available_tasks", {"project_id": "PID00007"}),
    ],
)
def test_malformed_arguments_fail_with_structured_validation_error(
    name: str, arguments: dict[str, Any]
) -> None:
    with pytest.raises(ToolFailure) as excinfo:
        validate_tool_input(_spec(name), arguments)
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert translated.hint  # Section 10.5 error rule
    assert translated.next_action
    assert translated.retryable is False


def test_non_object_arguments_are_rejected() -> None:
    with pytest.raises(ToolFailure):
        validate_tool_input(_spec("get_task_details"), ["not", "an", "object"])


# --- the wire surface (list_tools + tools/call) ----------------------------------


def test_list_tools_advertises_the_declared_schemas_verbatim(runtime: ToolRuntime) -> None:
    server = create_server(build_settings(), runtime=runtime)
    tools = asyncio.run(server.list_tools())
    assert [tool.name for tool in tools] == list(CORE_TOOL_NAMES)
    by_name = {tool.name: tool for tool in tools}
    for spec in TOOL_SPECS:
        assert by_name[spec.name].input_schema == dict(spec.input_schema)


def test_tools_call_rejects_unknown_properties_with_json_payload(runtime: ToolRuntime) -> None:
    server = create_server(build_settings(), runtime=runtime)
    with pytest.raises(ToolError) as excinfo:
        asyncio.run(
            server.call_tool("get_task_details", {"task_id": "PID00007-T004", "project_id": "X"})
        )
    prefix = "Error executing tool get_task_details: "
    payload = json.loads(str(excinfo.value).removeprefix(prefix))
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["hint"] and payload["next_action"]
    assert payload["retryable"] is False
