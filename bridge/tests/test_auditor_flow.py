"""MT-3.5-03 — the auditor flow with auditor rules integration.

Acceptance source: plan-doc-series/m3-audit-policy-merge/wp-3.5-bridge-audit-tools/
MT-3.5-03-auditor-flow.md (parent plan Sections 11.2, 10.5, 10.6, 10.8, 8.2
T11–T14, 9.4; FR-AUD-01/02; ADR-009).

The chain: an independent session lists ``to_be_audited`` (role=auditor),
claims one (T11 through WP-3.3's endpoint), checks the branch out read-only via
the Section 10.8 helper, then submits a structured verdict — the *backend*
Policy Engine decides T13/T14, never the bridge (ADR-09). Auditor rules reach
the agent on both channels: the claim response (role-specific render) and the
connect-time initialize instructions (both role blocks, since the role is not
yet known at connect — MT-3.5-03).

The unit battery pins the flow seams at the transport's send seam; the live
chain (gated on ``ORCHESTRATOR_BRIDGE_LIVE_TESTS=1`` + ``wp16-pg``) drives the
real backend end to end and asserts the backend-produced outcome.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.git_helper import (
    GitHelperError,
    create_or_switch_branch,
    run_git,
)
from orchestrator_bridge.rules import render_connect_rules
from orchestrator_bridge.server import create_server
from orchestrator_bridge.tools.audit_verdict import submit_audit_verdict
from orchestrator_bridge.tools.available_tasks import list_available_tasks
from orchestrator_bridge.tools.claim import claim_task
from orchestrator_bridge.tools.context import get_project_context
from orchestrator_bridge.tools.errors import ToolFailure
from tests import _live_backend
from tests.conftest import FakeBackend, build_runtime, build_settings
from tests.git_fixtures import make_repo

_AUDITABLE_ID = "PID00007-T004"
_CLAIM_PATH = endpoint("claim").path.format(id=_AUDITABLE_ID)
_WORK_PATH = endpoint("work_list").path.format(pid="PID00007")
_VERDICT_PATH = endpoint("audit_verdict").path.format(id=_AUDITABLE_ID)

_TO_BE_AUDITED_ROW = {
    "id": _AUDITABLE_ID,
    "project_id": "PID00007",
    "title": "Add invoice export",
    "state": "to_be_audited",
    "test_command": "pytest -q tests/billing",
    "target_scope": ["src/**"],
    "acceptance_criteria": ["Export runs green"],
}
_AUDITOR_LEASE = {
    "task_id": _AUDITABLE_ID,
    "assigned_agent": "auditor-1",
    "session_id": "fixture-session-0001",
    "role": "auditor",
    "lease_generation": 2,
    "lease_acquired_at": "2026-10-12T10:00:00Z",
    "lease_expires_at": "2026-10-12T10:45:00Z",
    "lease_hard_cap_at": "2026-10-12T14:00:00Z",
    "last_checkpoint": None,
    "failure_retry_count": 0,
}


def _auditor_backend() -> FakeBackend:
    """A fake offering the auditor's claim (T11) against a to_be_audited row."""
    fake = FakeBackend()
    fake.route(
        "POST",
        _CLAIM_PATH,
        200,
        {
            "task": _TO_BE_AUDITED_ROW,
            "lease": _AUDITOR_LEASE,
            "rules_block": {"standard_rules": [], "project_rules": ""},
        },
    )
    return fake


# --- role integration: the wire carries role; the rules arrive per role -------


def test_auditor_claim_sends_role_and_renders_the_auditor_rules() -> None:
    """T11 intent reaches the backend (role on the wire) and the auditor block
    is the delivered rules text (Section 10.6 auditor obligations)."""
    fake = _auditor_backend()
    result = claim_task(
        build_runtime(fake),
        task_id=_AUDITABLE_ID,
        agent_identifier="auditor-1",
        role="auditor",
    )
    (call,) = fake.calls_to("POST", _CLAIM_PATH)
    assert call.body["role"] == "auditor"  # WP-3.3 ClaimRequest role field
    rules = result["rules"]
    assert rules["role"] == "auditor"
    text = rules["text"]
    assert "full test and lint matrix" in text
    assert "Report honest confidence" in text
    # The auditor block, not the coder block, is what an auditor claim delivers.
    assert "Work only on the assigned branch" not in text
    assert result["lease"]["role"] == "auditor"
    assert result["lease"]["generation"] == 2


def test_auditor_list_sends_the_role_filter() -> None:
    fake = FakeBackend()
    fake.route(
        "GET",
        _WORK_PATH,
        200,
        {"results": [_TO_BE_AUDITED_ROW], "next_cursor": None},
    )
    result = list_available_tasks(build_runtime(fake), role="auditor")
    (call,) = fake.calls_to("GET", _WORK_PATH)
    assert "role=auditor" in call.query
    assert result["role"] == "auditor"
    assert result["count"] == 1
    assert result["tasks"][0]["state"] == "to_be_audited"


# --- rules reach the agent on both channels (Sections 10.6, 10.7) ------------


def test_initialize_instructions_carry_both_role_blocks() -> None:
    """Connect time shows coder *and* auditor rules (role not yet chosen)."""
    runtime = build_runtime(_auditor_backend())
    server = create_server(build_settings(), runtime=runtime)
    instructions = server.instructions
    assert isinstance(instructions, str)
    # Both Section 10.6 blocks are present before any claim is made.
    assert "Coder rules (Section 10.6):" in instructions
    assert "Auditor rules (Section 10.6):" in instructions
    assert "8. Provide a clear execution summary." in instructions  # coder
    assert "Report honest confidence" in instructions  # auditor
    # The owner's project rules are appended once, after both blocks.
    assert "Project rule: run the tests." in instructions
    assert instructions.index("8.") < instructions.index("Project rule:")


def test_context_rules_are_byte_identical_to_the_instructions() -> None:
    """G-08: one render path — get_project_context matches the instructions."""
    runtime = build_runtime(_auditor_backend())
    server = create_server(build_settings(), runtime=runtime)
    payload = get_project_context(runtime)
    assert server.instructions == payload["rules"]
    assert "Auditor rules (Section 10.6):" in payload["rules"]


def test_connect_render_is_the_shared_helper_for_both_channels() -> None:
    """Both connect channels draw from render_connect_rules (single source)."""
    text = render_connect_rules(
        project_rules="Keep it deterministic.",
        policy_summary={"lease_duration_minutes": 45},
    )
    assert "Coder rules (Section 10.6):" in text
    assert "Auditor rules (Section 10.6):" in text
    assert text.count("Keep it deterministic.") == 1  # appended once


# --- read-only checkout through the Section 10.8 helper ----------------------


def test_read_only_checkout_switches_and_never_pushes_resets_or_deletes(
    tmp_path: Path,
) -> None:
    """The auditor inspects the branch via the helper's read-only operations;
    the capability guard refuses push/reset/delete (Section 10.8)."""
    repo = make_repo(tmp_path / "repo")
    run_git(repo, ["switch", "-q", "-c", "feat/PID00007-T004", "main"])
    run_git(repo, ["switch", "-q", "main"])

    switched = create_or_switch_branch(repo, "feat/PID00007-T004", default_branch="main")
    assert switched.branch == "feat/PID00007-T004"
    assert switched.created is False  # branch existed; we only switched
    assert run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip() == (
        "feat/PID00007-T004"
    )

    # The structural allowlist refuses every mutating/network operation.
    for args in (["push", "origin", "main"], ["reset", "--hard", "HEAD"], ["push", "--force"]):
        with pytest.raises(GitHelperError) as excinfo:
            run_git(repo, args)
        assert "refuses" in excinfo.value.message


# --- outcome honesty: the tool reports; the backend decides (ADR-009) --------


def test_verdict_tool_reports_backend_outcome_and_fencing_pair() -> None:
    """The tool forwards the fencing pair and reports the backend's task state
    verbatim — it never marks T13/T14 itself."""
    fake = FakeBackend()
    fake.route(
        "POST",
        _VERDICT_PATH,
        201,
        {
            "report": {"id": "rep-0007", "verdict": "pass", "confidence": 4},
            "task": {
                "id": _AUDITABLE_ID,
                "state": "to_be_audited",
                "version": 5,
                "review_reason": None,
                "merge_status": "pending",  # T13: engine-approved, merge pending
            },
            "trigger": "audit_verdict_pass",
            "decision": {"approve": True, "reason": None},
        },
    )
    runtime = build_runtime(fake)
    runtime.record_lease(_AUDITABLE_ID, 2)  # the auditor claim's generation
    result = submit_audit_verdict(
        runtime,
        task_id=_AUDITABLE_ID,
        verdict="pass",
        confidence=4,
        evidence={"commands": [{"label": "tests", "command": "pytest -q", "exit_code": 0}]},
    )
    (call,) = fake.calls_to("POST", _VERDICT_PATH)
    assert call.body["session_id"] == "fixture-session-0001"
    assert call.body["lease_generation"] == 2  # ADR-012 fencing pair
    # The reported state is the backend's own — the bridge never invents it.
    assert result["task"]["state"] == "to_be_audited"
    assert result["task"]["merge_status"] == "pending"


def test_auditor_lease_expired_surfaces_stop_and_reclaim_guidance() -> None:
    """T12 audit-lease expiry is a structured stop-and-re-claim error."""
    fake = FakeBackend()
    fake.route(
        "POST",
        _VERDICT_PATH,
        409,
        {
            "error": {
                "code": "LEASE_EXPIRED",
                "message": "The audit lease expired.",
                "retryable": False,
                "details": None,
                "correlation_id": "corr-t12",
            }
        },
    )
    runtime = build_runtime(fake)
    runtime.record_lease(_AUDITABLE_ID, 2)
    with pytest.raises(ToolFailure) as excinfo:
        submit_audit_verdict(
            runtime,
            task_id=_AUDITABLE_ID,
            verdict="pass",
            confidence=4,
            evidence={"commands": [{"label": "t", "command": "pytest", "exit_code": 0}]},
        )
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.LEASE_EXPIRED
    assert translated.next_action and "claim_task" in translated.next_action


# --- live end-to-end chain against the real backend (Section 18) -------------


@pytest.mark.skipif(
    _live_backend.skip_reason() is not None,
    reason=_live_backend.skip_reason() or "unreachable",
)
class TestLiveAuditorChain:
    """The full list → claim → checkout → verdict chain on the real backend."""

    @pytest.fixture(scope="class")
    def live(self):  # type: ignore[no-untyped-def]
        backend = _live_backend.start_live_backend()
        try:
            yield backend
        finally:
            _live_backend.stop_live_backend(backend)

    def test_live_auditor_chain_produces_backend_outcome(
        self, live: _live_backend.LiveBackend, tmp_path: Path
    ) -> None:
        """An independent auditor session lists, claims (T11), checks the branch
        out read-only, submits a pass verdict, and the backend decides T13/T14."""
        from orchestrator_bridge.git_helper import create_or_switch_branch as checkout
        from tests.test_core_tools_live import _bound

        runtime = _bound(live, live.tokens[0], allow_gate=True)
        assert live.auditable_task is not None

        # 1. list — the auditor sees to_be_audited work.
        listing = list_available_tasks(runtime, role="auditor", limit=50)
        assert listing["role"] == "auditor"
        offered = {row["id"] for row in listing["tasks"]}
        assert live.auditable_task in offered

        # 2. claim — T11, independence via WP-3.3 (session is bridge-minted and
        # differs from the seed's coder session).
        claimed = claim_task(
            runtime,
            task_id=str(live.auditable_task),
            agent_identifier="live-auditor",
            role="auditor",
        )
        assert claimed["lease"]["role"] == "auditor"
        # The Section 10.6 auditor rules are in the claim response.
        assert "full test and lint matrix" in claimed["rules"]["text"]

        # 3. read-only checkout via the Section 10.8 helper (a local fixture
        # repo standing in for the auditor's clone of the task branch).
        repo = make_repo(tmp_path / "repo")
        branch = str(claimed["branch"])
        run_git(repo, ["switch", "-q", "-c", branch, "main"])
        run_git(repo, ["switch", "-q", "main"])
        switched = checkout(repo, branch, default_branch="main")
        assert switched.created is False

        # 4. verdict — a pass verdict; the backend Policy Engine decides.
        verdict = submit_audit_verdict(
            runtime,
            task_id=str(live.auditable_task),
            verdict="pass",
            confidence=5,
            evidence={
                "commands": [{"label": "tests", "command": "pytest -q", "exit_code": 0}],
                "lint_clean": True,
            },
            acceptance_criteria_results=[{"criterion": "Export runs green", "met": True}],
        )
        task_state = verdict["task"]
        assert task_state["id"] == live.auditable_task
        # T13 (engine approve → merge pending) or T14 (escalate → in_human_review)
        # are the only backend-decided outcomes; the bridge reported, not chose.
        if task_state["state"] == "to_be_audited":
            assert task_state["merge_status"] == "pending"  # T13
        else:
            assert task_state["state"] == "in_human_review"  # T14
            assert task_state["review_reason"]
