"""MT-3.5-01/02 — submit_audit_verdict schema and evidence validation.

Acceptance source: plan-doc-series/m3-audit-policy-merge/
wp-3.5-bridge-audit-tools/MT-3.5-01-verdict-schema.md (the registered tool
spec is Section 10.5's auditor verdict shape field for field) and
MT-3.5-02-evidence-validation.md (bridge-boundary validation with
field-naming guidance before the endpoint call; valid payloads forwarded
unchanged — FR-AUD-02).
"""

from __future__ import annotations

from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.tools import TOOLS
from orchestrator_bridge.tools.audit_verdict import submit_audit_verdict, validate_verdict_payload
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES
from tests.conftest import FakeBackend, build_runtime

_TASK_ID = "PID00007-T004"
_VERDICT_PATH = endpoint("audit_verdict").path.format(id=_TASK_ID)

_EVIDENCE = {
    "commands": [
        {
            "label": "tests",
            "command": "uv run pytest -q",
            "exit_code": 0,
            "summary": "42 passed",
            # Auditor-supplied extras survive verbatim (FR-AUD-02).
            "duration_seconds": 12.4,
        }
    ],
    "lint_clean": True,
}

_VALID_ARGS: dict[str, Any] = {
    "task_id": _TASK_ID,
    "verdict": "pass",
    "confidence": 4,
    "evidence": _EVIDENCE,
}


def _backend(response: Any = None) -> tuple[FakeBackend, dict[str, Any]]:
    body = response or {
        "report": {"id": "rep-0001", "verdict": "pass", "confidence": 4},
        "task": {"id": _TASK_ID, "state": "done"},
    }
    fake = FakeBackend()
    fake.route("POST", _VERDICT_PATH, 201, body)
    return fake, body


# --- MT-3.5-01: the registered schema (Section 10.5, field for field) ----------


def test_verdict_tool_is_registered_in_catalog_order() -> None:
    assert "submit_audit_verdict" in CORE_TOOL_NAMES
    assert CORE_TOOL_NAMES.index("submit_audit_verdict") == (
        CORE_TOOL_NAMES.index("release_task") + 1
    )


def test_schema_is_the_section_10_5_verdict_shape() -> None:
    schema = TOOLS["submit_audit_verdict"].input_schema
    assert schema["required"] == ["task_id", "verdict", "confidence", "evidence"]
    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert set(properties) == {
        "task_id",
        "verdict",
        "confidence",
        "notes",
        "evidence",
        "acceptance_criteria_results",
    }
    assert properties["verdict"]["enum"] == ["pass", "flag_risk", "fail"]
    assert properties["confidence"]["minimum"] == 1
    assert properties["confidence"]["maximum"] == 5
    evidence = properties["evidence"]
    assert evidence["required"] == ["commands"]
    command = evidence["properties"]["commands"]["items"]
    assert command["required"] == ["label", "command", "exit_code"]
    assert command["properties"]["exit_code"]["type"] == "integer"
    criterion = properties["acceptance_criteria_results"]["items"]
    assert criterion["required"] == ["criterion", "met"]


def test_verdict_declares_the_backend_rejections() -> None:
    declared = set(TOOLS["submit_audit_verdict"].errors)
    assert {
        ErrorCode.TASK_NOT_FOUND,
        ErrorCode.TASK_STATE_CONFLICT,
        ErrorCode.LEASE_EXPIRED,
        ErrorCode.LEASE_NOT_OWNED,
        ErrorCode.ROLE_NOT_PERMITTED,
        ErrorCode.AUDITOR_SAME_AS_CODER,
    } <= declared


# --- MT-3.5-02: validation before the wire, verbatim passthrough after --------


def test_valid_payload_is_forwarded_unchanged_with_the_fencing_pair() -> None:
    fake, _ = _backend()
    runtime = build_runtime(fake)
    result = submit_audit_verdict(
        runtime,
        task_id=_TASK_ID,
        verdict="pass",
        confidence=4,
        evidence=_EVIDENCE,
        notes="Everything is green.",
        acceptance_criteria_results=[{"criterion": "Export runs green", "met": True}],
    )
    call = fake.calls_to("POST", _VERDICT_PATH)[0]
    assert call.body["evidence"] == _EVIDENCE  # verbatim, extras included
    assert call.body["session_id"] == "fixture-session-0001"
    assert call.body["lease_generation"] == 0  # never claimed in this session
    assert call.body["verdict"] == "pass" and call.body["confidence"] == 4
    assert call.body["acceptance_criteria_results"] == [
        {"criterion": "Export runs green", "met": True}
    ]
    assert call.headers.get("Idempotency-Key")  # mutating call (headers.md)
    assert result["report"]["id"] == "rep-0001"
    assert result["task"]["state"] == "done"


def test_optional_fields_stay_optional_on_the_wire() -> None:
    fake, _ = _backend()
    runtime = build_runtime(fake)
    submit_audit_verdict(
        runtime, task_id=_TASK_ID, verdict="fail", confidence=2, evidence=_EVIDENCE
    )
    body = fake.calls_to("POST", _VERDICT_PATH)[0].body
    assert "notes" not in body and "acceptance_criteria_results" not in body


def test_empty_commands_are_rejected_with_the_field_named() -> None:
    with pytest.raises(ToolFailure) as excinfo:
        validate_verdict_payload(evidence={"commands": []}, acceptance_criteria_results=None)
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert translated.details == {"field": "evidence.commands"}
    assert "evidence.commands" in translated.next_action


@pytest.mark.parametrize(
    ("entry", "field"),
    [
        ({"label": " ", "command": "pytest", "exit_code": 0}, "evidence.commands[0].label"),
        ({"label": "t", "command": "", "exit_code": 0}, "evidence.commands[0].command"),
        ({"label": "t", "command": "pytest", "exit_code": "0"}, "evidence.commands[0].exit_code"),
    ],
)
def test_bad_command_entries_name_the_exact_field(entry: dict[str, Any], field: str) -> None:
    with pytest.raises(ToolFailure) as excinfo:
        validate_verdict_payload(evidence={"commands": [entry]}, acceptance_criteria_results=None)
    assert excinfo.value.translated.details == {"field": field}


def test_criterion_without_text_is_rejected_with_the_field_named() -> None:
    with pytest.raises(ToolFailure) as excinfo:
        validate_verdict_payload(
            evidence=_EVIDENCE, acceptance_criteria_results=[{"criterion": "", "met": True}]
        )
    assert excinfo.value.translated.details == {"field": "acceptance_criteria_results[0].criterion"}


def test_none_acceptance_criteria_is_allowed() -> None:
    validate_verdict_payload(evidence=_EVIDENCE, acceptance_criteria_results=None)


def test_backend_rejections_pass_through_with_their_catalog_code() -> None:
    fake, _ = _backend()
    fake.route(
        "POST",
        _VERDICT_PATH,
        409,
        {
            "error": {
                "code": "AUDITOR_SAME_AS_CODER",
                "message": "The same agent may not audit its own work.",
                "retryable": False,
                "details": None,
                "correlation_id": "corr-audit",
            }
        },
    )
    runtime = build_runtime(fake)
    with pytest.raises(ToolFailure) as excinfo:
        submit_audit_verdict(
            runtime, task_id=_TASK_ID, verdict="pass", confidence=4, evidence=_EVIDENCE
        )
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.AUDITOR_SAME_AS_CODER
    assert translated.correlation_id == "corr-audit"
