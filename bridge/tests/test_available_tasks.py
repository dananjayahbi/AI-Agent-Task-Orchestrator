"""MT-2.4-02 — get_available_tasks with role parameter and filters.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.4-core-tools/
MT-2.4-02-available-tasks.md (parent plan Sections 9.2 work row, 10.5;
FR-MCP-03, FR-LEA-01). Backend mocked at the send seam; the role-visibility
authorization itself is the backend's (Section 12.2 — the bridge never
weakens it client-side).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.tools.available_tasks import list_available_tasks, task_descriptor
from orchestrator_bridge.tools.errors import ToolFailure
from tests.conftest import FakeBackend, build_runtime, envelope_wire

_WORK = "/api/v1/projects/PID00007/work"

_TASK_ROW = {
    "id": "PID00007-T004",
    "project_id": "PID00007",
    "title": "Add invoice export",
    "priority": "high",
    "state": "pending",
    "depends_on": [],
    "description": "Full markdown description that must not ride the descriptor.",
    "acceptance_criteria": ["criterion 1"],
    "test_command": "pytest -q",
}


def _backend(*rows: Mapping[str, Any], next_cursor: str | None = None) -> FakeBackend:
    fake = FakeBackend()
    fake.route("GET", _WORK, 200, {"results": list(rows), "next_cursor": next_cursor})
    return fake


def test_coder_view_uses_the_default_role() -> None:
    fake = _backend(_TASK_ROW)
    result = list_available_tasks(build_runtime(fake))
    (call,) = fake.calls_to("GET", _WORK)
    assert "role=coder" in call.query
    assert "page_size=25" in call.query
    assert result["role"] == "coder"
    assert result["count"] == 1


def test_descriptors_are_compact_and_never_carry_content() -> None:
    fake = _backend(_TASK_ROW)
    (task,) = list_available_tasks(build_runtime(fake))["tasks"]
    assert set(task) == {"id", "title", "priority", "state", "depends_on"}
    assert "description" not in task and "acceptance_criteria" not in task


def test_attachment_descriptors_pass_through_but_never_content() -> None:
    row = {
        **_TASK_ROW,
        "attachments": [
            {"id": 7, "filename": "design.png", "processing_status": "ready"},
            {"id": 8, "filename": "scan.pdf", "processing_status": "pending"},
        ],
    }
    (task,) = list_available_tasks(build_runtime(_backend(row)))["tasks"]
    assert task["attachments"] == row["attachments"]  # descriptors, Section 10.5
    assert all("content" not in item for item in task["attachments"])


def test_auditor_view_forwards_the_role_filter() -> None:
    fake = _backend({**_TASK_ROW, "state": "to_be_audited"})
    result = list_available_tasks(build_runtime(fake), role="auditor")
    (call,) = fake.calls_to("GET", _WORK)
    assert "role=auditor" in call.query
    assert result["tasks"][0]["state"] == "to_be_audited"


def test_priority_filter_and_limit_reach_the_backend() -> None:
    fake = _backend()
    list_available_tasks(build_runtime(fake), priority_filter="urgent", limit=7)
    (call,) = fake.calls_to("GET", _WORK)
    assert "priority=urgent" in call.query
    assert "page_size=7" in call.query


def test_empty_result_is_a_calm_response() -> None:
    result = list_available_tasks(build_runtime(_backend()))
    assert result == {"role": "coder", "count": 0, "tasks": []}


def test_next_cursor_is_surfaced_when_the_page_is_not_the_end() -> None:
    result = list_available_tasks(build_runtime(_backend(_TASK_ROW, next_cursor="abc")))
    assert result["next_cursor"] == "abc"


@pytest.mark.parametrize(
    "code", ["AUTH_FORBIDDEN_PROJECT", "VALIDATION_ERROR", "ROLE_NOT_PERMITTED"]
)
def test_backend_errors_surface_with_hint_and_next_action(code: str) -> None:
    fake = FakeBackend()
    fake.route("GET", _WORK, 403, json_envelope(code))
    with pytest.raises(ToolFailure) as excinfo:
        list_available_tasks(build_runtime(fake))
    translated = excinfo.value.translated
    assert translated.code is ErrorCode(code)
    assert translated.hint and translated.next_action


def test_malformed_envelope_is_a_structured_server_error() -> None:
    fake = FakeBackend()
    fake.route("GET", _WORK, 200, {"results": "not-a-list"})
    with pytest.raises(ToolFailure) as excinfo:
        list_available_tasks(build_runtime(fake))
    assert excinfo.value.translated.code is ErrorCode.SERVER_ERROR


def test_task_descriptor_keeps_documented_fields_only() -> None:
    assert task_descriptor({**_TASK_ROW, "worker_agent_id": "someone"}) == {
        "id": "PID00007-T004",
        "title": "Add invoice export",
        "priority": "high",
        "state": "pending",
        "depends_on": [],
    }


def json_envelope(code: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(envelope_wire(403, code, f"backend said {code}").body)
    return payload
