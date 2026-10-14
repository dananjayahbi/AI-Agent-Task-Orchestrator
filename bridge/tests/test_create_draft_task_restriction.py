"""MT-3.8-03 — tool-path restriction cases (the bridge half of the suite).

UC-10 / G-19 / Sections 10.5, 12.2, 19: the decomposer's denials must
hold through the **MCP tool surface** too, so a refactor of tool
registration can never widen decomposer power behind the backend's
back. The backend enforces (Section 12.2 is server-side — the bridge
never re-implements authorization); these cases prove the surface
*carries* the refusal as a structured, catalog-coded ``ToolFailure``
(hint + next action per the Section 10.5 error rule) instead of a crash
or a retry:

* positive control — ``create_draft_task`` still answers a ``draft``
  (the one Yes cell; MT-3.8-02's wire contract, re-asserted here so the
  restriction run proves grant *and* refusal together);
* claim (T4 ``pending`` / T11 ``to_be_audited``) — decomposer-scoped
  calls surface ``ROLE_NOT_PERMITTED`` from the catalog;
* ``submit_audit_verdict`` — same refusal, same code;
* every tool above *declares* ``ROLE_NOT_PERMITTED`` in its contract
  errors (Section 10.5 registration rule).

The decomposition/create path itself lives in ``test_create_draft_task``
(MT-3.8-02) — this module's name carries the ``create_draft_task``
keyword so ``pytest -k create_draft_task`` runs the pair together.

Run with ``pytest bridge/tests -k create_draft_task -q``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.tools import TOOLS
from orchestrator_bridge.tools.audit_verdict import submit_audit_verdict
from orchestrator_bridge.tools.claim import claim_task
from orchestrator_bridge.tools.create_draft_task import create_draft_task
from orchestrator_bridge.tools.errors import ToolFailure
from tests.conftest import FakeBackend, build_runtime, envelope_wire

_CREATE_PATH = endpoint("task_create_draft").path.format(pid="PID00007")
_PENDING_ID = "PID00007-T004"
_AUDIT_ID = "PID00007-T005"
_CLAIM_PATH = endpoint("claim").path.format(id=_PENDING_ID)
_AUDIT_CLAIM_PATH = endpoint("claim").path.format(id=_AUDIT_ID)
_VERDICT_PATH = endpoint("audit_verdict").path.format(id=_AUDIT_ID)

_EVIDENCE: dict[str, Any] = {
    "commands": [
        {
            "label": "tests",
            "command": "uv run pytest -q",
            "exit_code": 0,
            "summary": "42 passed",
        }
    ]
}

_DRAFT_ROW: dict[str, Any] = {
    "id": "PID00007-T009",
    "project_id": "PID00007",
    "title": "Split the billing module",
    "description": "Decomposition slice.",
    "acceptance_criteria": [],
    "target_scope": ["src/billing/**"],
    "test_command": "",
    "priority": "medium",
    "state": "draft",
    "version": 1,
}


def _denied_backend(*paths: str) -> FakeBackend:
    """A backend answering every listed POST path with the catalog 403."""
    envelope = json.loads(
        envelope_wire(403, "ROLE_NOT_PERMITTED", "backend said ROLE_NOT_PERMITTED").body
    )
    fake = FakeBackend()
    for path in paths:
        fake.route("POST", path, 403, envelope)
    return fake


def _assert_role_denial(excinfo: pytest.ExceptionInfo[ToolFailure]) -> None:
    """One refusal: the catalog code verbatim, never retryable."""
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.ROLE_NOT_PERMITTED
    assert translated.retryable is False
    assert translated.hint and translated.next_action  # Section 10.5 rule


# --- positive control: the grant stays open in the same run -------------------


def test_create_draft_task_positive_control_answers_a_draft() -> None:
    """The one Yes cell through the tool surface: 201 → ``draft``."""
    fake = FakeBackend()
    fake.route("POST", _CREATE_PATH, 201, _DRAFT_ROW)

    result = create_draft_task(build_runtime(fake), title="Split the billing module")

    assert result["task_id"] == "PID00007-T009"
    assert result["state"] == "draft"
    assert result["version"] == 1


# --- claim: T4 pending and T11 to_be_audited both refused ---------------------


@pytest.mark.parametrize(
    ("path", "role"),
    [(_CLAIM_PATH, "coder"), (_AUDIT_CLAIM_PATH, "auditor")],
    ids=["claim-pending-coder", "claim-to-be-audited-auditor"],
)
def test_create_draft_task_restriction_claim_surfaces_role_not_permitted(
    path: str, role: str
) -> None:
    """The tool carries the backend's T4/T11 denial as a ToolFailure."""
    fake = _denied_backend(path)
    runtime = build_runtime(fake)

    with pytest.raises(ToolFailure) as excinfo:
        claim_task(
            runtime,
            task_id=path.rsplit("/", 2)[-2],
            agent_identifier="decomposer-agent",
            role=role,
        )
    _assert_role_denial(excinfo)


# --- submit verdict: the auditor write cell refused ---------------------------


def test_create_draft_task_restriction_verdict_surfaces_role_not_permitted() -> None:
    """``submit_audit_verdict`` carries the same catalog refusal."""
    fake = _denied_backend(_VERDICT_PATH)

    with pytest.raises(ToolFailure) as excinfo:
        submit_audit_verdict(
            build_runtime(fake),
            task_id=_AUDIT_ID,
            verdict="pass",
            confidence=4,
            evidence=_EVIDENCE,
        )
    _assert_role_denial(excinfo)


# --- contract: the refusal code is declared, not improvised --------------------


def test_create_draft_task_restriction_tools_declare_role_not_permitted() -> None:
    """Section 10.5 registration: every restricted tool lists the code."""
    for name in ("create_draft_task", "claim_task", "submit_audit_verdict"):
        assert ErrorCode.ROLE_NOT_PERMITTED in {ErrorCode(e) for e in TOOLS[name].errors}, name
