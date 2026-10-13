"""Shared plumbing for the WP-3.4 Policy Engine suites (MT-3.4-01 … 07).

Not a test module (no ``test_`` prefix), mirroring ``tests/wp15_helpers``
and friends. Four concerns every WP-3.4 suite shares:

* **Registry + seam restore (mandatory)** — :func:`restore_policy_registry`
  snapshots the transition registry and pins **both** decision seams to
  their fail-closed defaults around every test, so an engine installed
  by one test never leaks into the next (the wp32/wp33 rule).
* **The engine under test** — :func:`policy_engine_installed` runs the
  real wiring (``ensure_policy_engine_wired``) a test can then drive
  through the seams and the real endpoints.
* **The table-driven harness** — WP-3.4's Wave 7 acceptance ("each
  rule pass/fail and combinations"): :class:`PolicyCase` +
  :func:`run_policy_table` take (context, expected decision, expected
  per-rule failures, expected primary reason) cases against the pure
  evaluator. :func:`clean_context` is the all-pass baseline each rule
  suite perturbs.
* **Audited-flow seeds** — a ``to_be_audited`` task carrying a real
  stored patch artifact (so R5(b) can scan added lines) and the
  independent-coder resolution the G-20 guard needs; plus canonical
  patches and evidence bodies per scenario.

Local media rides along (autouse): submissions and seeds store patch
artifacts, so every suite runs against a per-test ``MEDIA_ROOT``.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.audit.decision import set_audit_decision_hook
from apps.audit.policy import (
    DECISION_APPROVE,
    DECISION_ESCALATE,
    ENGINE_VERSION,
    RULE_SLOTS,
    EvaluationResult,
    EvidenceCommand,
    PolicyContext,
    evaluate,
)
from apps.audit.policy.wiring import ensure_policy_engine_wired
from apps.projects.models import Project
from apps.tasks.models import Task, TaskResolution, TaskState
from apps.tasks.services.patch_parse import parse_unified_diff
from apps.tasks.services.resolutions import store_patch_artifact
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY
from apps.tasks.state_machine.transitions_submission import set_policy_decision_hook

from .wp15_helpers import install_event_recorder, make_task, reset_hooks  # noqa: F401
from .wp16_helpers import active_policy_project  # noqa: F401
from .wp33_helpers import (  # noqa: F401  (re-exported for suites)
    JsonAPIClient,
    agent_client,
    claim_as_auditor,
    issue_agent_token,
    login_owner_client,
    make_pending_task,
    verdict_body,
)

__all__ = [
    "CLEAN_PATCH",
    "COMMIT_SHA",
    "CRITICAL_PATCH",
    "MIGRATION_PATCH",
    "OUT_OF_SCOPE_PATCH",
    "SECRET_LINE_PATCH",
    "SENSITIVE_GLOB_PATCH",
    "PolicyCase",
    "active_policy_project",
    "agent_client",
    "auditable_with_patch",
    "clean_context",
    "claim_as_auditor",
    "install_event_recorder",
    "issue_agent_token",
    "login_owner_client",
    "make_pending_task",
    "make_task",
    "policy_engine_installed",
    "restore_policy_registry",
    "rule_result_rows",
    "run_policy_table",
    "verdict_body",
]

COMMIT_SHA = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret


# --- canonical patches (each a real single-file git-format diff) -----------


def _patch(path: str, *added: str, removed: Sequence[str] = ()) -> str:
    """One file-section git-format patch with honest hunk counts."""
    old_lines = 1 + len(removed)
    new_lines = 1 + len(added)
    body = "".join(f"-{line}\n" for line in removed)
    body += "".join(f"+{line}\n" for line in added)
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -1,{old_lines} +1,{new_lines} @@\n"
        " context-line\n"
        f"{body}"
    )


#: A clean in-scope change: one added line in ``src/app.py``.
CLEAN_PATCH = _patch("src/app.py", "print('hello')")
#: An out-of-scope change (R2).
OUT_OF_SCOPE_PATCH = _patch("docs/readme.md", "docs line")
#: A CI/CD change (R3 — matches the default critical-path globs).
CRITICAL_PATCH = _patch(".github/workflows/ci.yml", "on: push")
#: An alembic migration (R4 — matches the default migration globs).
MIGRATION_PATCH = _patch("alembic/versions/0001_init.py", "revision = '0001'")
#: An env file (R5(a) — matches the default sensitive-config globs).
SENSITIVE_GLOB_PATCH = _patch(".env.local", "APP_MODE=dev")
#: A clean path whose added line carries a secret-like literal (R5(b)).
SECRET_LINE_PATCH = _patch(
    "src/app.py",
    'api_key = "AKIA1234567890ABCDEF"',  # pragma: allowlist secret
)


# --- the table-driven harness (Section 19 WP-3.4 acceptance) ----------------


@dataclass(frozen=True)
class PolicyCase:
    """One table row: context in, expected engine verdict out."""

    case_id: str
    context: PolicyContext
    expect_decision: str
    expect_failed: frozenset[str] = frozenset()
    expect_reason: str | None = None


def run_policy_table(cases: Sequence[PolicyCase]) -> None:
    """Run the pure evaluator over each case and assert the full contract.

    Every case additionally proves the framework invariants: all nine
    slots present in R1…R9 order, engine version stamped, reason set
    exactly on failing rules, and approve iff nothing failed.
    """
    for case in cases:
        result = evaluate(case.context)
        _assert_result_shape(result)
        failed = frozenset(outcome.rule for outcome in result.failed_rules)
        assert result.decision == case.expect_decision, case.case_id
        assert failed == set(case.expect_failed), (case.case_id, failed)
        assert result.primary_reason == case.expect_reason, case.case_id


def _assert_result_shape(result: EvaluationResult) -> None:
    """The invariants every evaluation satisfies (MT-3.4-01 acceptance)."""
    assert result.engine_version == ENGINE_VERSION
    assert tuple(outcome.rule for outcome in result.rule_results) == RULE_SLOTS
    for outcome in result.rule_results:
        assert (outcome.review_reason is None) == outcome.passed
    assert result.approved == (result.decision == DECISION_APPROVE)
    if result.approved:
        assert result.primary_reason is None and not result.failed_rules
    else:
        assert result.decision == DECISION_ESCALATE
        assert result.primary_reason is not None


def rule_result_rows(payload: Any) -> list[dict[str, Any]]:
    """The persisted §7.2 ``policy_rule_results`` list, type-narrowed."""
    assert isinstance(payload, list), "the engine always persists the full list"
    return payload


# --- the all-pass baseline context each suite perturbs ---------------------


def clean_context(**overrides: Any) -> PolicyContext:
    """An all-pass context: every rule green under default-shaped policy."""
    base: dict[str, Any] = {
        "target_scope": ("src/**",),
        "changed_files": ("src/app.py",),
        "insertions": 10,
        "deletions": 5,
        "added_lines": ("print('hello')",),
        "critical_path_globs": (".github/workflows/*",),
        "migration_path_globs": ("alembic/versions/*",),
        "sensitive_config_globs": (".env*", "**/*.pem"),
        "autonomous_diff_threshold_lines": 250,
        "auditor_min_confidence": 4,
        "auto_complete_enabled": True,
        "evidence_commands": (EvidenceCommand("tests", "pytest -q", 0),),
        "auditor_confidence": 5,
        "proposed_verdict": "pass",
    }
    base.update(overrides)
    return PolicyContext(**base)


# --- fixtures every WP-3.4 module imports (the wp16 promotion trick) -------


@pytest.fixture(autouse=True)
def restore_policy_registry() -> Iterator[None]:
    """Snapshot the registry; pin both seams fail-closed; restore after."""
    ensure_registered()
    snapshot = DEFAULT_REGISTRY.specs()
    set_audit_decision_hook(None)
    set_policy_decision_hook(None)
    try:
        yield
    finally:
        DEFAULT_REGISTRY.replace_all(snapshot)
        set_audit_decision_hook(None)  # fail-closed default must stay ambient
        set_policy_decision_hook(None)
        reset_hooks()


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — fresh budget per test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def local_media(tmp_path: Path) -> Iterator[None]:
    """Per-test ``MEDIA_ROOT`` so patch storage never touches ``/media``."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield


@pytest.fixture
def policy_engine_installed() -> None:
    """The real wiring under test (both seams; MT-3.4-07)."""
    ensure_policy_engine_wired()


# --- audited-flow seeds (resolution + stored patch + independent coder) ----


def auditable_with_patch(
    project: Project,
    index: int,
    *,
    patch: str = CLEAN_PATCH,
    target_scope: Sequence[str] = ("src/**",),
    coder_session: str = "sess_wp34_coder",
    attempt: int = 1,
    diff_summary: dict[str, Any] | None = None,
    changed_files: Sequence[str] | None = None,
) -> Task:
    """A ``to_be_audited`` task whose resolution carries a *stored* patch.

    The real T7 outcome without spending a submission: authoritative
    parse of *patch* (MT-3.2-03), the artifact row + stored body (so
    R5(b) can scan), and the G-20 independence inputs. ``diff_summary``
    /``changed_files`` override the parsed values for degraded-row
    scenarios (R6's unprovable-stats table case).
    """
    task = make_task(
        project,
        index,
        state=TaskState.TO_BE_AUDITED,
        attempt_number=attempt,
        audit_required=True,
        target_scope=list(target_scope),
    )
    parsed = parse_unified_diff(patch)
    resolution = TaskResolution.objects.create(
        task=task,
        attempt_number=attempt,
        branch_name=f"feat/{project.pk}-T{index:03d}",
        commit_sha=COMMIT_SHA,
        execution_summary="wp34 seed submission",
        submitted_by_session=coder_session,
        diff_summary=diff_summary if diff_summary is not None else parsed.as_diff_summary(),
        changed_files=(
            list(changed_files) if changed_files is not None else list(parsed.changed_files)
        ),
    )
    store_patch_artifact(resolution, patch)
    return task
