"""MT-3.8-02 — ``create_draft_task``: draft-only creation with ``depends_on``.

Acceptance source: plan-doc-series/m3-audit-policy-merge/
wp-3.8-decomposer/MT-3.8-02-create-draft-task.md (parent plan Sections 10.5,
11.3, 7.2, 7.3, 8.2 T1; UC-10, G-19). Contract tests run against the
``conftest.FakeBackend`` send seam (documented wire contract — the
``TaskCreateSerializer`` body and the Section 9.2 error envelope); the
integration-marked test at the bottom drives the real stack (opt-in live
backend, MT-3.8-01's decomposer permission now landed) end to end.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.config import load_settings
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.errors import SessionOpenError
from orchestrator_bridge.manifest import StartupBinding
from orchestrator_bridge.server import create_server
from orchestrator_bridge.session import (
    CAPABILITY_UNKNOWN,
    CLIENT_NAME,
    AgentSession,
    ProjectContext,
    new_session_id,
    open_session,
)
from orchestrator_bridge.tools import TOOLS
from orchestrator_bridge.tools.create_draft_task import create_draft_task
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.runtime import ToolRuntime
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES
from orchestrator_bridge.transport import ApiClient
from tests import _live_backend
from tests.conftest import FakeBackend, build_runtime, build_settings

_CREATE_PATH = endpoint("task_create_draft").path.format(pid="PID00007")

_VALID_ARGS: dict[str, Any] = {
    "title": "Wire the export endpoint",
    "criteria": ["Export runs green"],
    "scope": ["src/export/**"],
    "test_command": "uv run pytest -q tests/export",
    "priority": "high",
    "depends_on": ["PID00007-T003"],
}


def _stored_task(**overrides: Any) -> dict[str, Any]:
    """The WP-1.4 ``TaskSerializer`` shape a create answers with (T1: draft)."""
    task: dict[str, Any] = {
        "id": "PID00007-T009",
        "project_id": "PID00007",
        "title": "Wire the export endpoint",
        "description": "",
        "acceptance_criteria": ["Export runs green"],
        "target_scope": ["src/export/**"],
        "test_command": "uv run pytest -q tests/export",
        "priority": "high",
        "state": "draft",
        "version": 1,
        "depends_on": ["PID00007-T003"],
    }
    task.update(overrides)
    return task


def _backend(response: Any = None) -> FakeBackend:
    fake = FakeBackend()
    fake.route("POST", _CREATE_PATH, 201, response if response is not None else _stored_task())
    return fake


# --- the registered contract (Section 10.5; MT acceptance item 1) ---------------


def test_create_draft_task_is_registered_in_catalog_order() -> None:
    assert "create_draft_task" in CORE_TOOL_NAMES
    assert CORE_TOOL_NAMES.index("create_draft_task") == (
        CORE_TOOL_NAMES.index("submit_audit_verdict") + 1
    )


def test_schema_has_exactly_the_section_10_5_inputs_and_no_project_id() -> None:
    schema = TOOLS["create_draft_task"].input_schema
    assert schema["required"] == ["title"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {
        "title",
        "description",
        "criteria",
        "scope",
        "test_command",
        "priority",
        "depends_on",
    }
    # No project id (Section 10.3/10.5 binding rule — the global scan in
    # test_tool_schemas.py also covers it) and no state argument: the
    # draft-only guarantee is structural, not a default (MT risk note).
    assert "state" not in schema["properties"]
    assert "project_id" not in schema["properties"]


def test_schema_declares_role_restriction_error() -> None:
    declared = set(TOOLS["create_draft_task"].errors)
    assert ErrorCode.ROLE_NOT_PERMITTED in declared
    assert ErrorCode.VALIDATION_ERROR in declared


# --- the wire contract (documented backend behavior) ---------------------------


def test_create_posts_the_task_create_contract_without_state() -> None:
    fake = _backend()
    runtime = build_runtime(fake)

    result = create_draft_task(
        runtime,
        title="Wire the export endpoint",
        criteria=["Export runs green"],
        scope=["src/export/**"],
        test_command="uv run pytest -q tests/export",
        priority="high",
        depends_on=["PID00007-T003"],
    )

    (call,) = fake.calls_to("POST", _CREATE_PATH)
    assert call.body == {
        "title": "Wire the export endpoint",
        "description": "",
        "acceptance_criteria": ["Export runs green"],
        "target_scope": ["src/export/**"],
        "test_command": "uv run pytest -q tests/export",
        "priority": "high",
        "depends_on": ["PID00007-T003"],
        # Never a state, never a project_id, never a session pair — draft-only
        # is structural and the path carries the bound project.
    }
    assert "state" not in call.body
    assert "project_id" not in call.body
    assert call.headers["Idempotency-Key"]  # mutating POST (NFR-12; ADR-012)

    assert result["task_id"] == "PID00007-T009"
    assert result["state"] == "draft"
    assert result["depends_on"] == ["PID00007-T003"]
    assert result["version"] == 1
    assert "publishes it (T2)" in result["next_action"]


def test_omitted_optionals_send_documented_defaults() -> None:
    fake = _backend(_stored_task(title="Minimal", acceptance_criteria=[], target_scope=[]))
    runtime = build_runtime(fake)

    create_draft_task(runtime, title="Minimal")

    (call,) = fake.calls_to("POST", _CREATE_PATH)
    assert call.body == {
        "title": "Minimal",
        "description": "",
        "acceptance_criteria": [],
        "target_scope": [],
        "test_command": "",
        "priority": "medium",
        # depends_on omitted entirely when not supplied — the backend treats
        # an absent list as "no edges" (MT-1.4-05), never as a clear signal.
    }
    assert "depends_on" not in call.body


def test_empty_depends_on_list_is_forwarded_as_empty() -> None:
    fake = _backend(_stored_task(depends_on=[]))
    runtime = build_runtime(fake)

    result = create_draft_task(runtime, title="No edges", depends_on=[])

    (call,) = fake.calls_to("POST", _CREATE_PATH)
    assert call.body["depends_on"] == []
    assert result["depends_on"] == []


# --- backend refusals surface as catalog-coded tool failures --------------------


def test_role_denial_surfaces_as_role_not_permitted() -> None:
    """MT-3.8-01's path: a non-decomposer token is refused server-side and
    the bridge translates the catalog code verbatim (Section 19.3 — the
    bridge never re-implements authorization)."""
    fake = FakeBackend()
    fake.routes[("POST", _CREATE_PATH)] = (
        403,
        {
            "error": {
                "code": "ROLE_NOT_PERMITTED",
                "message": "Only the owner, a decomposer agent or a device can create drafts.",
                "retryable": False,
                "details": None,
                "correlation_id": "corr-fixture",
            }
        },
    )
    runtime = build_runtime(fake)

    with pytest.raises(ToolFailure) as excinfo:
        create_draft_task(runtime, title="Denied")

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.ROLE_NOT_PERMITTED
    assert translated.retryable is False
    assert translated.hint and translated.next_action  # Section 10.5 error rule


def test_unknown_dependency_answer_refuses_with_validation_error() -> None:
    """The backend's MT-1.4-05 refusal (unknown/foreign/self/cyclic id —
    VALIDATION_ERROR, whole create rolled back) surfaces untranslated."""
    fake = FakeBackend()
    fake.routes[("POST", _CREATE_PATH)] = (
        400,
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "depends_on: unknown task id PID00007-T999.",
                "retryable": False,
                "details": {"field": "depends_on"},
                "correlation_id": "corr-fixture",
            }
        },
    )
    runtime = build_runtime(fake)

    with pytest.raises(ToolFailure) as excinfo:
        create_draft_task(runtime, title="Bad edge", depends_on=["PID00007-T999"])

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert translated.retryable is False


def test_malformed_create_response_fails_loudly() -> None:
    fake = _backend([{"id": "not-an-object"}])
    runtime = build_runtime(fake)

    with pytest.raises(ToolFailure) as excinfo:
        create_draft_task(runtime, title="Weird")

    assert excinfo.value.translated.code is ErrorCode.SERVER_ERROR


# --- server surface (tools/call over the registered tool) ----------------------


def test_tools_call_create_draft_task_returns_the_stored_draft(
    fake_backend: FakeBackend,
) -> None:
    import asyncio
    import json

    from mcp_types import CallToolResult

    fake_backend.route("POST", _CREATE_PATH, 201, _stored_task())
    runtime = build_runtime(fake_backend)
    server = create_server(build_settings(), runtime=runtime)

    result = asyncio.run(server.call_tool("create_draft_task", dict(_VALID_ARGS)))

    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    parsed = json.loads(result.content[0].text)  # type: ignore[union-attr]
    assert parsed["task_id"] == "PID00007-T009"
    assert parsed["state"] == "draft"


def test_tools_call_rejects_a_smuggled_state_argument(runtime: ToolRuntime) -> None:
    """Draft-only on the wire too: a state argument is a validation error,
    so the tool can never drift toward publish capability."""
    import asyncio

    server = create_server(build_settings(), runtime=runtime)
    with pytest.raises(ToolError) as excinfo:
        asyncio.run(server.call_tool("create_draft_task", {"title": "X", "state": "pending"}))
    assert "VALIDATION_ERROR" in str(excinfo.value)


# --- the real-backend expectation (integration; MT-3.8-01 landed) --------------

_LIVE_RUN_COMMAND = (
    "ORCHESTRATOR_BRIDGE_LIVE_TESTS=1 docker start wp16-pg && "
    "uv run --directory bridge pytest tests/test_create_draft_task.py -q -m integration"
)

# Evaluated at import time (the test_core_tools_live.py pattern): the
# conftest hermetic fixture strips ORCHESTRATOR_* variables per test, so a
# fixture-time check would always see the opt-in flag as unset.
_LIVE_SKIP_REASON = _live_backend.skip_reason()


@pytest.fixture(scope="module")
def live_backend() -> Iterator[_live_backend.LiveBackend]:
    """One migrated, seeded backend for the module; torn down afterwards."""
    if _LIVE_SKIP_REASON is not None:
        pytest.skip(f"{_LIVE_SKIP_REASON} — run: {_LIVE_RUN_COMMAND}")
    backend = _live_backend.start_live_backend()
    try:
        yield backend
    finally:
        _live_backend.stop_live_backend(backend)


def _manifest(live: _live_backend.LiveBackend) -> dict[str, object]:
    return {
        "schema_version": 1,
        "project_id": live.project_id,
        "project_name": "Bridge IT Project",
        "orchestrator_api": live.api_base_url,
        "default_branch": "main",
        "auto_branch_prefix": f"feat/{live.project_id}-",
        "audit_required_default": True,
    }


def _session_opening_only(client: ApiClient, binding: StartupBinding) -> AgentSession:
    """Open just the backend session (no context reads) — the gate fallback.

    Mirrors ``test_core_tools_live._session_opening_only``: the recorded
    backend gate on agent read-only access (``GET /projects/{pid}``) can
    answer ``ROLE_NOT_PERMITTED``; the create route itself is MT-3.8-01's
    activated matrix row and does not depend on the context cache.
    """
    session_id = new_session_id()
    response = client.request(
        "POST",
        endpoint("session_open").path,
        body={
            "id": session_id,
            "client_name": CLIENT_NAME,
            "capability": CAPABILITY_UNKNOWN,
            "transport": "stdio",
        },
    )
    agent_session_id = (
        str(response.get("id"))
        if isinstance(response, Mapping) and isinstance(response.get("id"), str)
        else session_id
    )
    return AgentSession(
        agent_session_id=agent_session_id,
        context=ProjectContext(
            project_id=binding.project_id,
            name="(backend gate: agent project read pending)",
            rules="",
            policy_summary={},
        ),
    )


def _bound(live: _live_backend.LiveBackend, token: str) -> ToolRuntime:
    """A full bridge startup against the live backend for *token*."""
    settings = dataclasses.replace(
        load_settings(env={"ORCHESTRATOR_AGENT_TOKEN": token}, config_path=Path("no-such.toml")),
        timeout_seconds=30.0,
        retry_max_attempts=3,
    )
    binding = StartupBinding(manifest_path=Path("orchestrator.json"), manifest=_manifest(live))
    client = ApiClient.for_binding(binding, settings)
    try:
        session = open_session(binding, settings, client=client)
    except SessionOpenError as exc:
        if "ROLE_NOT_PERMITTED" not in str(exc):
            raise
        session = _session_opening_only(client, binding)
    return ToolRuntime.from_session(binding, client, session)


@pytest.mark.integration
def test_live_decomposer_token_creates_a_draft_with_dependencies(
    live_backend: _live_backend.LiveBackend,
) -> None:
    """MT-3.8-01 + MT-3.8-02 together, against the real stack.

    A decomposer-scoped agent token calling ``create_draft_task`` creates a
    task stored as ``draft`` (T1 — the only transition the tool can cause)
    with ``depends_on`` persisted; an unknown dependency is refused with
    ``VALIDATION_ERROR`` and no task appears; and a coder-scoped token is
    refused with ``ROLE_NOT_PERMITTED`` (Section 12.2 matrix — the denial
    is the backend's, surfaced verbatim). Run: ``''' + _LIVE_RUN_COMMAND + '''``.
    """
    if live_backend.decomposer_token is None:
        pytest.fail("live seed did not mint the decomposer token")
    decomposer = _bound(live_backend, live_backend.decomposer_token)

    parent = create_draft_task(
        decomposer,
        title="Bridge IT: decomposed parent",
        description="Created live through the MCP tool.",
        criteria=["Child depends on this draft"],
        scope=["src/**"],
        test_command="uv run pytest -q",
    )
    assert parent["state"] == "draft"
    assert parent["task_id"].startswith(f"{live_backend.project_id}-T")
    assert parent["version"] == 1

    child = create_draft_task(
        decomposer,
        title="Bridge IT: decomposed child",
        depends_on=[parent["task_id"]],
    )
    assert child["state"] == "draft"
    assert child["depends_on"] == [parent["task_id"]]

    with pytest.raises(ToolFailure) as excinfo:
        create_draft_task(decomposer, title="Bad edge", depends_on=["PID00007-T999"])
    assert excinfo.value.translated.code is ErrorCode.VALIDATION_ERROR

    coder = _bound(live_backend, live_backend.tokens[0])
    with pytest.raises(ToolFailure) as excinfo:
        create_draft_task(coder, title="Coder cannot create")
    assert excinfo.value.translated.code is ErrorCode.ROLE_NOT_PERMITTED
