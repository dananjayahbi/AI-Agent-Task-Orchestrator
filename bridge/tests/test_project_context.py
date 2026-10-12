"""MT-2.4-06 — get_project_context for cheap orientation.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.4-core-tools/
MT-2.4-06-project-context.md (parent plan Sections 10.3 step 5, 10.5;
FR-MCP-03). Cache-hit makes zero backend calls; the miss path (a resumed
session) fetches once through the shared client; failures are structured
retryable errors, never crashes.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.server import create_server
from orchestrator_bridge.tools import TOOLS
from orchestrator_bridge.tools.context import get_project_context
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.runtime import ToolRuntime
from orchestrator_bridge.tools.validation import validate_tool_input
from orchestrator_bridge.transport import ApiClient, WireResponse
from tests.conftest import FakeBackend, build_runtime, build_settings, envelope_wire


def test_cache_hit_answers_with_zero_backend_calls(
    fake_backend: FakeBackend, runtime: ToolRuntime
) -> None:
    result = get_project_context(runtime)
    assert fake_backend.calls == []  # cheap: no transport activity at all
    assert result["project_id"] == "PID00007"
    assert result["project_name"] == "Tea Factory ERP"
    assert result["rules"] == "Project rule: run the tests."
    assert result["policy_summary"] == {"max_concurrent_tasks": 1, "lease_duration_minutes": 45}


def test_second_call_still_makes_zero_backend_calls(
    runtime: ToolRuntime, fake_backend: FakeBackend
) -> None:
    get_project_context(runtime)
    get_project_context(runtime)
    assert fake_backend.calls == []


def test_cache_miss_fetches_once_then_serves_from_cache() -> None:
    fake = FakeBackend()
    fake.route(
        "GET",
        "/api/v1/projects/PID00007",
        200,
        {"id": "PID00007", "name": "Tea ERP", "system_prompt_rules": "Rule."},
    )
    fake.route("GET", "/api/v1/projects/PID00007/policy", 200, {"max_concurrent_tasks": 2})
    runtime = build_runtime(fake)
    runtime.context = None  # the MT's "resumed session" state: cache missing
    first = get_project_context(runtime)
    assert first["project_name"] == "Tea ERP"
    assert len(fake.calls) == 2  # project + policy, once
    second = get_project_context(runtime)
    assert second == first
    assert len(fake.calls) == 2  # still cached — no further fetch


def test_backend_down_on_miss_is_a_structured_retryable_error() -> None:
    def _down(
        method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: float
    ) -> WireResponse:
        del method, url, headers, body, timeout
        raise OSError("connection refused")

    fake = FakeBackend()  # the send seam is overridden below
    runtime = build_runtime(fake)
    runtime.context = None
    runtime.client = ApiClient.for_binding(runtime.binding, build_settings(), send=_down)
    with pytest.raises(ToolFailure) as excinfo:
        get_project_context(runtime)
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.SERVER_ERROR
    assert translated.retryable is True  # Section 10.10: a retry can succeed
    assert translated.hint and translated.next_action


def test_auth_failure_on_miss_surfaces_the_canonical_code() -> None:
    fake = FakeBackend()
    fake.route(
        "GET",
        "/api/v1/projects/PID00007",
        403,
        json.loads(envelope_wire(403, "AUTH_FORBIDDEN_PROJECT", "denied").body),
    )
    runtime = build_runtime(fake)
    runtime.context = None
    with pytest.raises(ToolFailure) as excinfo:
        get_project_context(runtime)
    assert excinfo.value.translated.code is ErrorCode.AUTH_FORBIDDEN_PROJECT


def test_no_inputs_beyond_the_empty_object() -> None:
    assert validate_tool_input(TOOLS["get_project_context"], {}) == {}
    with pytest.raises(ToolFailure):
        validate_tool_input(TOOLS["get_project_context"], {"project_id": "PID00007"})


def test_payload_contains_no_tasks_users_or_secrets(runtime: ToolRuntime) -> None:
    result = get_project_context(runtime)
    assert set(result) == {"project_id", "project_name", "rules", "policy_summary"}


def test_tool_registration_serves_the_cache_answer() -> None:
    from mcp_types import CallToolResult

    runtime = build_runtime(FakeBackend())
    server = create_server(build_settings(), runtime=runtime)
    result = asyncio.run(server.call_tool("get_project_context", {}))
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert "Tea Factory ERP" in result.content[0].text  # type: ignore[union-attr]
