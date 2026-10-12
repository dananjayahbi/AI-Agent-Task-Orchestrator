"""MT-2.4-03 — get_task_details with criteria, scope, feedback.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.4-core-tools/
MT-2.4-03-task-details.md (parent plan Sections 9.2, 10.5; FR-MCP-03,
FR-TSK-02). Role gating of resolution exposure stays the backend's Section
12.2 authority — the tool takes only ``task_id`` and passes the row through.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.task_details import get_task_details
from tests.conftest import FakeBackend, build_runtime, envelope_wire

_DETAILS = "/api/v1/tasks/PID00007-T004"

_TASK_ROW = {
    "id": "PID00007-T004",
    "project_id": "PID00007",
    "title": "Add invoice export",
    "description": "Export invoices as CSV (markdown **allowed**).",
    "acceptance_criteria": ["CSV downloads with all columns"],
    "target_scope": ["src/billing/**"],
    "test_command": "pytest -q",
    "priority": "medium",
    "state": "in_progress",
    "version": 3,
    "depends_on": ["PID00007-T003"],
    "latest_feedback": "Attempt 1: flaky test in test_export.py.",
    "worker_agent_id": "coder-1",
    "claimed_role": "coder",
    "lease_expires_at": "2026-10-12T12:00:00Z",
    "failure_retry_count": 0,
    "attempt_number": 2,
}


def _backend(
    row: Mapping[str, Any] | None = None, status: int = 200, payload: Any = None
) -> FakeBackend:
    fake = FakeBackend()
    if payload is None and status == 200:
        payload = _TASK_ROW if row is None else row
    fake.route("GET", _DETAILS, status, payload)
    return fake


def test_full_payload_rides_the_details_call() -> None:
    result = get_task_details(build_runtime(_backend()), task_id="PID00007-T004")
    task = result["task"]
    # Section 10.5-listed content, all present (fixture tests per the MT).
    assert task["acceptance_criteria"] == ["CSV downloads with all columns"]
    assert task["target_scope"] == ["src/billing/**"]
    assert task["test_command"] == "pytest -q"
    assert task["latest_feedback"].startswith("Attempt 1")
    assert task["depends_on"] == ["PID00007-T003"]
    assert task["lease_expires_at"]


def test_only_task_id_is_accepted_and_no_project_call_is_made() -> None:
    fake = _backend()
    get_task_details(build_runtime(fake), task_id="PID00007-T004")
    paths = {(call.method, call.path) for call in fake.calls}
    assert paths == {("GET", _DETAILS)}  # exactly one call, project from the binding


def test_resolution_info_passes_through_when_the_backend_returns_it() -> None:
    """Auditor payload: the row may carry resolution info (Section 10.5) —
    the bridge relays it; *whether* an auditor/coder sees it is the
    backend's role split (Section 12.2), asserted here via the row shape."""
    row = {
        **_TASK_ROW,
        "resolution": {
            "execution_summary": "Shipped the export.",
            "git_branch": "feat/PID00007-T004",
            "commit_sha": "abc123",
        },
    }
    result = get_task_details(build_runtime(_backend(row)), task_id="PID00007-T004")
    assert result["task"]["resolution"]["execution_summary"] == "Shipped the export."


def test_coder_row_without_resolution_stays_free_of_it() -> None:
    result = get_task_details(build_runtime(_backend()), task_id="PID00007-T004")
    assert "resolution" not in result["task"]


def test_attachment_content_is_never_inlined_only_descriptors() -> None:
    row = {
        **_TASK_ROW,
        "attachments": [{"id": 7, "filename": "design.png", "processing_status": "ready"}],
    }
    result = get_task_details(build_runtime(_backend(row)), task_id="PID00007-T004")
    attachments = result["task"]["attachments"]
    assert attachments and all("content" not in item for item in attachments)


@pytest.mark.parametrize(
    ("status", "code"),
    [(404, "TASK_NOT_FOUND"), (403, "AUTH_FORBIDDEN_PROJECT"), (400, "VALIDATION_ERROR")],
)
def test_structured_errors_with_hint_and_next_action(status: int, code: str) -> None:
    envelope = json.loads(envelope_wire(status, code, f"backend said {code}").body)
    fake = FakeBackend()
    fake.route("GET", _DETAILS, status, envelope)
    with pytest.raises(ToolFailure) as excinfo:
        get_task_details(build_runtime(fake), task_id="PID00007-T004")
    translated = excinfo.value.translated
    assert translated.code is ErrorCode(code)
    assert translated.hint and translated.next_action


def test_malformed_response_is_a_structured_server_error() -> None:
    fake = _backend(payload=["not", "an", "object"])
    with pytest.raises(ToolFailure) as excinfo:
        get_task_details(build_runtime(fake), task_id="PID00007-T004")
    assert excinfo.value.translated.code is ErrorCode.SERVER_ERROR
