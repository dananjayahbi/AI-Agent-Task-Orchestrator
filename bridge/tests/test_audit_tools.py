"""MT-3.5-04 — auditor tool suite: chain, malformed-evidence guidance, rejections.

Acceptance source: plan-doc-series/m3-audit-policy-merge/wp-3.5-bridge-audit-tools/
MT-3.5-04-auditor-tool-tests.md (parent plan Sections 11.2, 10.5, 9.4, 18, 20.4,
20.5; FR-AUD-01/02). The cross-cutting behavioral slice WP-3.5's acceptance
demands: "invalid evidence rejected with guidance".

* the malformed-evidence matrix — missing ``evidence``; empty ``commands``;
  a command missing ``label``/``command``/``exit_code``; ``confidence`` 0 and
  6; a verdict outside ``pass``/``flag_risk``/``fail``; a criterion without
  ``met`` — each producing a Section 9.2 catalog code plus a hint and a next
  action identifying the offending field (guidance, not a bare rejection);
* cross-role and lease-owner rejections at the tool level
  (``ROLE_NOT_PERMITTED``, ``AUDITOR_SAME_AS_CODER``, ``LEASE_NOT_OWNED``);
* T12 audit-lease expiry surfacing as a stop-and-re-claim error;
* the schema contract reusing MT-3.5-01's Section 10.5 snapshot.

The chain against the real backend lives in ``test_auditor_flow.py``
(``-k auditor_flow``); this module pins the guidance matrix and the rejections
at the transport seam, so the whole battery stays green without the live stack.
"""

from __future__ import annotations

from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.tools import TOOLS
from orchestrator_bridge.tools.audit_verdict import (
    submit_audit_verdict,
    validate_verdict_payload,
)
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES, TOOL_SPECS
from orchestrator_bridge.tools.validation import validate_tool_input
from tests.conftest import FakeBackend, build_runtime, envelope_wire

_TASK_ID = "PID00007-T004"
_CLAIM_PATH = endpoint("claim").path.format(id=_TASK_ID)
_VERDICT_PATH = endpoint("audit_verdict").path.format(id=_TASK_ID)

_SPEC = next(spec for spec in TOOL_SPECS if spec.name == "submit_audit_verdict")

_VALID_EVIDENCE: dict[str, Any] = {
    "commands": [{"label": "tests", "command": "pytest -q", "exit_code": 0}],
    "lint_clean": True,
}


def _verdict_args(**overrides: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "task_id": _TASK_ID,
        "verdict": "pass",
        "confidence": 4,
        "evidence": _VALID_EVIDENCE,
    }
    args.update(overrides)
    return args


def _assert_guidance(translated: Any, *, field_token: str) -> None:
    """Every rejection carries the full three-element error contract.

    A Section 9.2 catalog code, a non-empty hint, a non-empty next action —
    and the offending field is named somewhere in the guidance (message,
    next_action or details), so the model can act on it (MT-3.5-04 risk note:
    a bare rejection would pass a weaker assertion).
    """
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert translated.hint
    assert translated.next_action
    haystack = " ".join(
        [
            translated.message,
            translated.next_action,
            str(translated.details) if translated.details else "",
        ]
    )
    assert field_token in haystack, f"{field_token!r} not named in {haystack!r}"


# --- the malformed-evidence matrix (Section 10.5 guidance) -------------------


def test_missing_evidence_is_rejected_with_guidance() -> None:
    args = _verdict_args()
    del args["evidence"]
    with pytest.raises(ToolFailure) as excinfo:
        validate_tool_input(_SPEC, args)
    _assert_guidance(excinfo.value.translated, field_token="evidence")


def test_empty_commands_are_rejected_with_the_field_named() -> None:
    with pytest.raises(ToolFailure) as excinfo:
        validate_verdict_payload(evidence={"commands": []}, acceptance_criteria_results=None)
    translated = excinfo.value.translated
    _assert_guidance(translated, field_token="evidence.commands")
    assert translated.details == {"field": "evidence.commands"}


@pytest.mark.parametrize(
    ("entry", "field_token"),
    [
        ({"command": "pytest", "exit_code": 0}, "label"),
        ({"label": "tests", "exit_code": 0}, "command"),
        ({"label": "tests", "command": "pytest"}, "exit_code"),
    ],
)
def test_command_missing_a_required_key_is_rejected_with_guidance(
    entry: dict[str, Any], field_token: str
) -> None:
    args = _verdict_args(evidence={"commands": [entry]})
    with pytest.raises(ToolFailure) as excinfo:
        validate_tool_input(_SPEC, args)
    _assert_guidance(excinfo.value.translated, field_token=field_token)


@pytest.mark.parametrize("confidence", [0, 6])
def test_confidence_out_of_bounds_is_rejected_with_guidance(confidence: int) -> None:
    args = _verdict_args(confidence=confidence)
    with pytest.raises(ToolFailure) as excinfo:
        validate_tool_input(_SPEC, args)
    _assert_guidance(excinfo.value.translated, field_token="confidence")


def test_verdict_outside_the_enum_is_rejected_with_guidance() -> None:
    args = _verdict_args(verdict="maybe")
    with pytest.raises(ToolFailure) as excinfo:
        validate_tool_input(_SPEC, args)
    _assert_guidance(excinfo.value.translated, field_token="verdict")


def test_criterion_without_met_is_rejected_with_guidance() -> None:
    args = _verdict_args(acceptance_criteria_results=[{"criterion": "Export runs"}])
    with pytest.raises(ToolFailure) as excinfo:
        validate_tool_input(_SPEC, args)
    _assert_guidance(excinfo.value.translated, field_token="met")


def test_criterion_without_text_is_rejected_with_the_field_named() -> None:
    with pytest.raises(ToolFailure) as excinfo:
        validate_verdict_payload(
            evidence=_VALID_EVIDENCE,
            acceptance_criteria_results=[{"criterion": "", "met": True}],
        )
    translated = excinfo.value.translated
    _assert_guidance(translated, field_token="acceptance_criteria_results[0].criterion")


def test_a_valid_payload_passes_both_validation_layers() -> None:
    """The matrix's control: a well-formed verdict clears schema + semantics."""
    validated = validate_tool_input(_SPEC, _verdict_args())
    validate_verdict_payload(evidence=validated["evidence"], acceptance_criteria_results=None)


# --- cross-role and lease-owner rejections (Sections 10.5, 12.2) -------------


def _backend_with_envelope(status: int, code: str, path: str) -> FakeBackend:
    envelope = envelope_wire(status, code, f"backend said {code}")
    import json

    fake = FakeBackend()
    fake.route("POST", path, status, json.loads(envelope.body))
    return fake


def test_coder_claiming_a_to_be_audited_task_is_role_refused() -> None:
    """A coder-role claim against an auditor-only state → ROLE_NOT_PERMITTED."""
    fake = _backend_with_envelope(403, "ROLE_NOT_PERMITTED", _CLAIM_PATH)
    from orchestrator_bridge.tools.claim import claim_task

    with pytest.raises(ToolFailure) as excinfo:
        claim_task(
            build_runtime(fake),
            task_id=_TASK_ID,
            agent_identifier="coder-1",
            role="coder",
        )
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.ROLE_NOT_PERMITTED
    assert translated.hint and translated.next_action


def test_same_session_auditor_verdict_is_refused() -> None:
    """WP-3.3's AUDITOR_SAME_AS_CODER surfaces at the verdict tool."""
    fake = _backend_with_envelope(409, "AUDITOR_SAME_AS_CODER", _VERDICT_PATH)
    with pytest.raises(ToolFailure) as excinfo:
        submit_audit_verdict(
            build_runtime(fake),
            task_id=_TASK_ID,
            verdict="pass",
            confidence=4,
            evidence=_VALID_EVIDENCE,
        )
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.AUDITOR_SAME_AS_CODER
    assert translated.hint and translated.next_action


def test_non_lease_owner_verdict_is_refused() -> None:
    """A session that does not hold the audit lease → LEASE_NOT_OWNED."""
    fake = _backend_with_envelope(403, "LEASE_NOT_OWNED", _VERDICT_PATH)
    with pytest.raises(ToolFailure) as excinfo:
        submit_audit_verdict(
            build_runtime(fake),
            task_id=_TASK_ID,
            verdict="pass",
            confidence=4,
            evidence=_VALID_EVIDENCE,
        )
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.LEASE_NOT_OWNED
    assert translated.hint and translated.next_action


def test_audit_lease_expiry_is_a_stop_and_reclaim_error() -> None:
    """T12: LEASE_EXPIRED's next action tells the auditor to stop and re-claim."""
    fake = _backend_with_envelope(409, "LEASE_EXPIRED", _VERDICT_PATH)
    with pytest.raises(ToolFailure) as excinfo:
        submit_audit_verdict(
            build_runtime(fake),
            task_id=_TASK_ID,
            verdict="pass",
            confidence=4,
            evidence=_VALID_EVIDENCE,
        )
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.LEASE_EXPIRED
    assert "claim_task" in translated.next_action  # stop-and-re-claim guidance


def test_rule_fail_verdict_reports_the_backend_t14_outcome() -> None:
    """T14: a rule-fail verdict lands `in_human_review` with the backend's
    enumerated reason — the bridge reports it, never chooses it (ADR-009;
    MT-3.5-04 acceptance: T13 *and* T14 outcomes appear correctly)."""
    # (Section 9.4 T14: verdict + any rule fails → in_human_review + reason)
    fake = FakeBackend()
    fake.route(
        "POST",
        _VERDICT_PATH,
        201,
        {
            "report": {"id": "rep-0008", "verdict": "flag_risk", "confidence": 3},
            "task": {
                "id": _TASK_ID,
                "state": "in_human_review",
                "version": 6,
                "review_reason": "test_failure",
                "merge_status": "blocked",
            },
            "trigger": "audit_verdict_flag_risk",
            "decision": {"approve": False, "reason": "test_failure"},
        },
    )
    result = submit_audit_verdict(
        build_runtime(fake),
        task_id=_TASK_ID,
        verdict="flag_risk",
        confidence=3,
        evidence=_VALID_EVIDENCE,
    )
    task_state = result["task"]
    assert task_state["state"] == "in_human_review"  # backend-decided T14
    assert task_state["review_reason"] == "test_failure"
    assert task_state["merge_status"] == "blocked"


# --- the schema contract (Section 18 contract row; reuses MT-3.5-01) --------


def test_schema_snapshot_matches_section_10_5() -> None:
    """Re-run MT-3.5-01's pinned snapshot so schema drift is caught here too."""
    from tests.test_audit_verdict_tool import test_schema_is_the_section_10_5_verdict_shape

    test_schema_is_the_section_10_5_verdict_shape()


def test_verdict_tool_declares_only_catalog_codes() -> None:
    """Section 20.4 item 5: only Section 9.2 catalog codes, no invented ones."""
    assert "submit_audit_verdict" in CORE_TOOL_NAMES
    spec = next(s for s in TOOL_SPECS if s.name == "submit_audit_verdict")
    for code in spec.errors:
        assert isinstance(code, ErrorCode)
    assert set(TOOLS["submit_audit_verdict"].errors) <= set(spec.errors)
