"""Harness self-tests for the MT-2.11-01 client-compatibility runner.

The runner is an instrument; these tests prove the instrument works before
any real client run trusts it (MT-2.11-01 acceptance, "Harness self-tests"):

* a full stdio run against a scripted loopback stub backend exercises all
  ten Section 10.5 tools across the three roles and records all four
  Section 10.7 prompts;
* the same run with a vision-capable session exercises the image packaging;
* a deliberately broken tool response (backend malformed claim; client-side
  non-JSON payload) fails the run - the detection the MT names;
* prompt absence is *reported*, never failed (NFR-08);
* error codes outside the Section 9.2 catalog fail the catalog check;
* the report's matrix row carries exactly the four Section 10.9 columns.

Selected with ``pytest -k conformance``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator_bridge.prompts import PROMPT_NAMES
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES
from tests.conformance.checks import (
    BANNER_MARKER,
    KNOWN_ERROR_CODES,
    check_error_catalog,
    check_prompt_render,
    check_prompts,
    check_tool_catalog,
)
from tests.conformance.connection import ToolCallResult
from tests.conformance.report import MATRIX_COLUMNS, ConformanceReport
from tests.conformance.runner import RunnerConfig, run_conformance
from tests.conformance.scenarios import RoleSession, run_coder_scenario
from tests.conftest import FIXTURE_TOKEN, MINIMAL_MANIFEST, StubHttpBackend
from tests.git_fixtures import make_repo

BRIDGE_ROOT = Path(__file__).resolve().parent.parent

PID = "PID00007"
T_CLAIM = f"{PID}-T004"
T_RELEASE = f"{PID}-T005"
T_AUDIT = f"{PID}-T006"
T_UNKNOWN = f"{PID}-T999"
ATTACHMENT_ID = "ATT-0001"

_UNTRUSTED = f"{BANNER_MARKER} The attachment content is unverified output."

_WORK_LIST = {
    "count": 3,
    "results": [
        {
            "id": T_CLAIM,
            "title": "Conformance claim task",
            "priority": "P2",
            "state": "pending",
            "depends_on": [],
        },
        {
            "id": T_RELEASE,
            "title": "Conformance release task",
            "priority": "P3",
            "state": "pending",
            "depends_on": [],
        },
        {
            "id": T_AUDIT,
            "title": "Conformance audit task",
            "priority": "P2",
            "state": "to_be_audited",
            "depends_on": [],
        },
    ],
}

_TEXT_CONTENT = {
    "attachment_id": ATTACHMENT_ID,
    "format": "text_ocr",
    "content": f"{_UNTRUSTED} A task board screenshot.",
    "description": f"{_UNTRUSTED} Mock UI screen.",
    "image_base64": None,
    "media_type": "image/png",
    "page_number": None,
    "total_pages": None,
    "token_count": None,
}

_IMAGE_CONTENT = {
    "attachment_id": ATTACHMENT_ID,
    "format": "image_base64",
    "content": None,
    "description": None,
    "image_base64": "aGVsbG8gY29uZm9ybWFuY2U=",  # base64 of a tiny stub body
    "media_type": "image/png",
    "page_number": None,
    "total_pages": None,
    "token_count": None,
}


def _envelope(code: str, message: str) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "hint": None,
            "next_action": None,
            "retryable": False,
            "details": None,
            "correlation_id": "corr-stub",
        }
    }


def _claim_body(task_id: str, role: str) -> dict[str, Any]:
    return {
        "task": {
            "id": task_id,
            "title": "Conformance task",
            "state": "in_progress",
            "test_command": "uv run pytest -q",
        },
        "lease": {
            "lease_generation": 1,
            "lease_acquired_at": "2029-12-31T23:00:00Z",
            "lease_expires_at": "2030-01-01T00:45:00Z",
            "lease_hard_cap_at": "2030-01-01T03:00:00Z",
            "assigned_agent": "conformance-probe",
            "session_id": "stub-session",
            "role": role,
            "last_checkpoint": None,
            "failure_retry_count": 0,
        },
        "rules_block": {"role": role, "text": "Backend rules block (Section 9.3)."},
    }


def register_happy_routes(
    stub: StubHttpBackend, *, vision: bool, broken_claim: bool = False
) -> None:
    """The full three-role happy path as canned (but stateful where needed) routes."""
    responses = stub.responses
    responses[("GET", f"/api/v1/projects/{PID}/work")] = (200, _WORK_LIST)
    responses[("GET", f"/api/v1/projects/{PID}/context")] = (
        200,
        {
            "project_id": PID,
            "project_name": "Tea Factory ERP",
            "rules": "Coder rules (Section 10.6):\nProject rules:\nProject rule.",
            "policy_summary": {"max_concurrent_tasks": 1, "lease_duration_minutes": 45},
        },
    )
    responses[("GET", f"/api/v1/tasks/{T_CLAIM}")] = (
        200,
        {
            "id": T_CLAIM,
            "state": "in_progress",
            "title": "Conformance claim task",
            "attachments": [
                {
                    "id": ATTACHMENT_ID,
                    "filename": "screenshot.png",
                    "mime_type": "image/png",
                    "is_image": True,
                    "processing_status": "ready",
                }
            ],
        },
    )
    responses[("GET", f"/api/v1/attachments/{ATTACHMENT_ID}")] = (
        200,
        {
            "attachment_id": ATTACHMENT_ID,
            "filename": "screenshot.png",
            "mime_type": "image/png",
            "is_image": True,
            "processing_status": "ready",
            "failure_reason": None,
        },
    )
    content_calls = {"count": 0}

    def content_route(_body: Any) -> tuple[int, Any]:
        content_calls["count"] += 1
        # Vision session: auto -> image, explicit text_ocr -> text, explicit
        # image_base64 -> image. Text-safe session: every read is text.
        if vision and content_calls["count"] in (1, 3):
            return (200, _IMAGE_CONTENT)
        return (200, _TEXT_CONTENT)

    responses[("GET", f"/api/v1/attachments/{ATTACHMENT_ID}/content")] = content_route

    claim_calls = {"count": 0}

    def claim_route(_body: Any) -> tuple[int, Any]:
        claim_calls["count"] += 1
        if broken_claim:
            # 200 with a missing rules_block: the bridge must turn this into
            # a structured SERVER_ERROR instead of inventing a shape.
            return (
                200,
                {"task": {"id": T_CLAIM, "state": "in_progress"}, "lease": {}},
            )
        if claim_calls["count"] == 1:
            return (200, _claim_body(T_CLAIM, "coder"))
        return (409, _envelope("TASK_ALREADY_CLAIMED", "task is already claimed"))

    responses[("POST", f"/api/v1/tasks/{T_CLAIM}/claim")] = claim_route
    responses[("POST", f"/api/v1/tasks/{T_RELEASE}/claim")] = (
        200,
        _claim_body(T_RELEASE, "coder"),
    )
    responses[("POST", f"/api/v1/tasks/{T_UNKNOWN}/claim")] = (
        404,
        _envelope("TASK_NOT_FOUND", "no such task"),
    )
    responses[("POST", f"/api/v1/tasks/{T_AUDIT}/claim")] = (
        200,
        _claim_body(T_AUDIT, "auditor"),
    )
    responses[("POST", f"/api/v1/tasks/{T_CLAIM}/checkpoints")] = (
        200,
        {
            "task_id": T_CLAIM,
            "checkpoint": {"id": "CHK-0001", "state": "in_progress", "percentage": 50},
            "lease_extended": True,
            "lease_expires_at": "2030-01-01T01:00:00Z",
            "lease_hard_cap_at": "2030-01-01T03:00:00Z",
            "capped": False,
            "next_checkpoint_due": "2030-01-01T00:50:00Z",
            "next_action": "continue",
        },
    )
    responses[("POST", f"/api/v1/tasks/{T_CLAIM}/resolution")] = (
        200,
        {
            "resolution": {"id": "RES-0001", "task_id": T_CLAIM},
            "task": {"id": T_CLAIM, "state": "to_be_audited", "review_reason": None},
            "trigger": "audit_required_default",
            "scope_violations": [],
        },
    )
    responses[("POST", f"/api/v1/tasks/{T_RELEASE}/release")] = (
        200,
        {"id": T_RELEASE, "state": "pending", "lease": None},
    )
    responses[("POST", f"/api/v1/tasks/{T_AUDIT}/audit-verdict")] = (
        200,
        {
            "report": {"id": "REP-0001", "verdict": "pass", "confidence": 4},
            "task": {"id": T_AUDIT, "state": "resolved"},
        },
    )
    responses[("POST", f"/api/v1/projects/{PID}/tasks")] = (
        201,
        {
            "id": f"{PID}-T101",
            "state": "draft",
            "title": "Conformance draft task (MT-2.11-01)",
            "priority": "P3",
            "depends_on": [],
            "version": 1,
        },
    )


def _repo_with_manifest(origin: str, tmp_path: Path) -> Path:
    manifest = dict(MINIMAL_MANIFEST)
    manifest["orchestrator_api"] = f"{origin}/api/v1"
    return make_repo(
        tmp_path / "conformance-repo",
        {"orchestrator.json": json.dumps(manifest), "README.md": "# conformance\n"},
    )


def _stdio_config(repo: Path, tmp_path: Path, *, capability: str | None) -> RunnerConfig:
    return RunnerConfig(
        manifest_path=repo / "orchestrator.json",
        repo_path=repo,
        project_id=PID,
        transport="stdio",
        coder_token=FIXTURE_TOKEN,
        auditor_token=FIXTURE_TOKEN,
        decomposer_token=FIXTURE_TOKEN,
        spool_dir=tmp_path / "spool",
        capability=capability,
        client_label="Hermetic stub client",
        expected_project_rules="Project rule.",
        cwd=BRIDGE_ROOT,
    )


# --- full-run self-tests (real stdio wire against the loopback stub) -----------


def test_text_only_full_run_exercises_catalog_prompts_and_matrix(
    stub_http_backend: StubHttpBackend, tmp_path: Path
) -> None:
    register_happy_routes(stub_http_backend, vision=False)
    repo = _repo_with_manifest(stub_http_backend.origin, tmp_path)
    report = run_conformance(_stdio_config(repo, tmp_path, capability="text_only"))

    assert report.passed, report.summary()
    assert sorted(report.tools_exercised) == sorted(CORE_TOOL_NAMES)
    assert report.prompts_surfaced == list(PROMPT_NAMES)
    assert report.prompts_absent == []
    row = report.matrix_row()
    assert list(row) == list(MATRIX_COLUMNS)
    assert row["Prompts surfaced"].startswith("yes")
    assert report.text_only_path_seen and not report.vision_path_seen
    assert report.images_column().startswith("no")
    # The Section 9.5 image gate answered with its catalog code.
    assert "ATTACHMENT_UNSUPPORTED_FORMAT" in report.observed_error_codes
    # The deliberate failure paths ran and only Section 9.2 codes were seen.
    assert "TASK_ALREADY_CLAIMED" in report.observed_error_codes
    assert "TASK_NOT_FOUND" in report.observed_error_codes
    assert set(report.observed_error_codes) <= KNOWN_ERROR_CODES


def test_vision_full_run_records_the_image_path(
    stub_http_backend: StubHttpBackend, tmp_path: Path
) -> None:
    register_happy_routes(stub_http_backend, vision=True)
    repo = _repo_with_manifest(stub_http_backend.origin, tmp_path)
    report = run_conformance(_stdio_config(repo, tmp_path, capability="vision"))

    assert report.passed, report.summary()
    assert report.vision_path_seen and not report.text_only_path_seen
    assert report.images_column().startswith("yes")


def test_broken_backend_claim_response_fails_the_run(
    stub_http_backend: StubHttpBackend, tmp_path: Path
) -> None:
    register_happy_routes(stub_http_backend, vision=False, broken_claim=True)
    repo = _repo_with_manifest(stub_http_backend.origin, tmp_path)
    report = run_conformance(_stdio_config(repo, tmp_path, capability=None))

    assert not report.passed
    failed_ids = {check.id for check in report.failures}
    assert "coder.claim_task" in failed_ids
    assert "SERVER_ERROR" in report.observed_error_codes
    assert set(report.observed_error_codes) <= KNOWN_ERROR_CODES


# --- unit self-tests (scripted connections, no subprocess) ---------------------


class _ScriptedConnection:
    """A minimal McpConnection answering each tool with a canned result."""

    def __init__(self, responses: dict[str, ToolCallResult]) -> None:
        self._responses = responses
        self.closed = False

    def initialize(self) -> dict[str, Any]:  # noqa: ARG002 - protocol surface
        return {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "scripted", "version": "0"},
            "instructions": "Coder rules (Section 10.6):\nProject rules:\nProject rule.",
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return []

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:  # noqa: ARG002
        return self._responses[name]

    def list_prompts(self) -> list[dict[str, Any]]:
        return []

    def get_prompt(self, name: str) -> dict[str, Any]:  # noqa: ARG002
        raise KeyError(name)

    def close(self) -> None:
        self.closed = True


def _text_result(name: str, payload: Any) -> ToolCallResult:
    return ToolCallResult(name=name, is_error=False, content=[{"type": "text", "text": payload}])


def test_broken_client_side_response_is_detected_and_fails_the_scenario() -> None:
    report = ConformanceReport(client_label="scripted", transport="injected")
    connection = _ScriptedConnection(
        {
            "get_project_context": _text_result(
                "get_project_context", json.dumps({"project_id": PID, "rules": "Project rule."})
            ),
            # The "backend" answered, but the payload is not JSON: a broken
            # wire the runner must surface instead of silently skipping.
            "get_available_tasks": _text_result("get_available_tasks", "<<<not json>>>"),
        }
    )
    session = RoleSession(report, connection, "coder")
    outcome = run_coder_scenario(report, session, capability=None, project_id=PID)

    assert outcome.claimed_task_id is None
    failed_ids = {check.id for check in report.failures}
    assert "coder.get_available_tasks" in failed_ids
    assert not report.passed


def test_prompt_absence_is_reported_not_failed() -> None:
    report = ConformanceReport(client_label="scripted", transport="injected")
    surfaced = check_prompts(report, [])

    assert surfaced == []
    assert report.prompts_surfaced == []
    assert report.prompts_absent == list(PROMPT_NAMES)
    assert report.failures == [] and report.passed
    assert report.prompts_column() == "no"
    prompt_check = next(check for check in report.checks if check.id == "connect.prompts")
    assert prompt_check.status == "reported"


def test_prompt_render_failure_is_a_failure() -> None:
    report = ConformanceReport(client_label="scripted", transport="injected")
    check_prompt_render(report, "orchestrator:start_work", None, error="boom")
    assert not report.passed
    assert report.prompt_render_failures == ["orchestrator:start_work"]
    check_prompt_render(report, "orchestrator:checkpoint", {"messages": []})
    assert report.prompt_render_failures == ["orchestrator:start_work", "orchestrator:checkpoint"]


def test_catalog_membership_check_rejects_invented_codes() -> None:
    report = ConformanceReport(client_label="scripted", transport="injected")
    report.note_error_code("NOT_A_CATALOG_CODE")
    check_error_catalog(report)
    assert [check.id for check in report.failures] == ["errors.catalog"]
    assert not report.passed

    clean = ConformanceReport(client_label="scripted", transport="injected")
    clean.note_error_code("TASK_NOT_FOUND")
    check_error_catalog(clean)
    assert clean.passed


def test_tool_catalog_check_fails_on_a_shrunk_advertisement() -> None:
    report = ConformanceReport(client_label="scripted", transport="injected")
    tools = [{"name": name, "inputSchema": {}} for name in CORE_TOOL_NAMES[:-1]]
    check_tool_catalog(report, "coder", tools)
    failed_ids = {check.id for check in report.failures}
    assert "coder.catalog.tools" in failed_ids


def test_matrix_columns_are_section_10_9_verbatim() -> None:
    assert MATRIX_COLUMNS == (
        "Transport",
        "Prompts surfaced",
        "Images in tool results",
        "Notes",
    )
    report = ConformanceReport(client_label="Custom agent", transport="stdio")
    row = report.matrix_row()
    assert list(row) == list(MATRIX_COLUMNS)
