"""Per-role conformance scenarios (MT-2.11-01; Sections 10.5, 10.6, 12.1).

The three role flows the MT pins, each as one function over a
:class:`RoleSession` (a connection plus its report):

* **coder** - orient (``get_project_context``) -> list (``get_available_tasks``)
  -> claim -> details -> attachment read (both packagings) -> checkpoint ->
  error paths (double claim, unknown task) -> submit or release;
* **auditor** - list ``to_be_audited`` -> claim -> ``submit_audit_verdict``;
* **decomposer** - ``create_draft_task`` only (Section 12.2 role restriction).

Every call records which Section 10.5 tool it exercised and any structured
error code it observed, so the report's catalog check and the matrix's tools
column come from the run itself, never from a hard-coded list.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES

from .checks import BANNER_MARKER, check_claim_rules
from .connection import McpConnection, ToolCallResult
from .report import CheckResult, ConformanceReport, Status

__all__ = [
    "CoderOutcome",
    "PreparedCommit",
    "RoleSession",
    "run_auditor_scenario",
    "run_coder_scenario",
    "run_decomposer_scenario",
    "tools_expected",
]


@dataclass
class PreparedCommit:
    """One committed branch tip the coder scenario submits (repo side)."""

    branch: str
    sha: str


class RoleSession:
    """One role's MCP connection plus its place in the report."""

    def __init__(self, report: ConformanceReport, connection: McpConnection, role: str) -> None:
        self.report = report
        self.connection = connection
        self.role = role

    def call(
        self, tool: str, arguments: dict[str, Any], *, expect_error: bool = False
    ) -> ToolCallResult:
        """One ``tools/call`` with per-check bookkeeping.

        An unexpected error or a non-JSON success payload records a *fail*
        (the broken-response detection the MT's harness self-tests prove);
        an ``expect_error`` call records nothing here - the caller asserts
        the observed code.
        """
        result = self.connection.call_tool(tool, arguments)
        self.report.note_tools(tool)
        if result.is_error:
            self.report.note_error_code(result.error_code())
            if not expect_error:
                self.record(
                    tool,
                    "fail",
                    f"unexpected structured error {result.error_code() or result.text_blocks[:1]}",
                )
        elif expect_error:
            self.record(tool, "fail", "expected a structured error, got success")
        elif result.payload() is None:
            self.record(
                tool,
                "fail",
                f"broken tool response: first text block is not JSON: {result.text_blocks[:1]}",
            )
        return result

    def expect_code(
        self, tool: str, arguments: dict[str, Any], expected: str, *, check_id: str
    ) -> None:
        """A deliberate failure path: assert the exact Section 9.2 code."""
        result = self.call(tool, arguments, expect_error=True)
        if not result.is_error:
            return  # the unexpected-success fail is already recorded
        observed = result.error_code()
        if observed == expected:
            self.record(check_id, "pass", f"{tool} answered {expected} as designed")
        else:
            self.record(
                check_id,
                "fail",
                f"{tool} answered {observed!r}, expected {expected}",
            )

    def ok(self, check_id: str, detail: str) -> None:
        self.record(check_id, "pass", detail)

    def record(self, check_id: str, status: Status, detail: str) -> None:
        self.report.add(CheckResult(f"{self.role}.{check_id}", self.role, status, detail))


@dataclass
class CoderOutcome:
    """What the coder scenario achieved - inputs to the auditor scenario."""

    claimed_task_id: str | None = None
    submitted_task_id: str | None = None
    released_task_id: str | None = None
    attachment_id: str | None = None


def _pick_task(tasks: list[dict[str, Any]], *, state: str) -> dict[str, Any] | None:
    for task in tasks:
        if task.get("state") == state:
            return task
    return None


def _tasks_of(result: ToolCallResult) -> list[dict[str, Any]]:
    payload = result.payload()
    if not isinstance(payload, dict):
        return []
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return []
    return [task for task in tasks if isinstance(task, dict)]


def run_coder_scenario(
    report: ConformanceReport,
    session: RoleSession,
    *,
    capability: str | None,
    project_id: str,
    prepare_commit: Callable[[str], PreparedCommit] | None = None,
    expected_project_rules: str | None = None,
    prefer_task_id: str | None = None,
) -> CoderOutcome:
    """The coder flow: orient, list, claim, details, attachment, checkpoint, submit/release."""
    outcome = CoderOutcome()
    assert session.role == "coder"

    context = session.call("get_project_context", {})
    if context.is_error or context.payload() is None:
        return outcome
    payload = context.payload()
    if (
        isinstance(payload, dict)
        and isinstance(payload.get("rules"), str)
        and payload.get("project_id") == project_id
    ):
        session.ok("orient", f"oriented on project {project_id} with merged rules block")
    else:
        session.ok("orient", "get_project_context answered (shape not asserted)")

    listing = session.call("get_available_tasks", {"role": "coder"})
    candidate: dict[str, Any] | None = None
    if not listing.is_error and listing.payload() is not None:
        tasks = _tasks_of(listing)
        if prefer_task_id is not None:
            candidate = next(
                (
                    task
                    for task in tasks
                    if task.get("id") == prefer_task_id and task.get("state") == "pending"
                ),
                None,
            )
        if candidate is None:
            candidate = _pick_task(tasks, state="pending")
        if candidate is None:
            session.record(
                "list", "fail", "no pending task in the coder work list - nothing to claim"
            )
    if candidate is None:
        return outcome
    task_id = str(candidate["id"])
    session.ok("list", f"work list offered pending task {task_id}")

    claim = session.call(
        "claim_task", {"task_id": task_id, "agent_identifier": "conformance-coder"}
    )
    claim_payload = claim.payload()
    if claim.is_error or not isinstance(claim_payload, dict):
        return outcome
    outcome.claimed_task_id = task_id
    branch = claim_payload.get("branch")
    lease = claim_payload.get("lease")
    rules = claim_payload.get("rules")
    lease_ok = isinstance(lease, dict) and lease.get("expires_at") is not None
    if isinstance(branch, str) and branch and lease_ok:
        session.ok("claim", f"claimed {task_id} on {branch} with a live lease")
    else:
        session.record(
            "claim",
            "fail",
            f"claim result missing branch/lease (Section 10.5): {claim_payload!r:.200}",
        )
    rules_text = rules.get("text") if isinstance(rules, dict) else None
    check_claim_rules(report, "coder", rules_text, expected_project_rules=expected_project_rules)

    # Deliberate failure paths while the task is held (Section 9.2 codes only).
    session.expect_code(
        "claim_task",
        {"task_id": task_id, "agent_identifier": "conformance-probe"},
        "TASK_ALREADY_CLAIMED",
        check_id="errors.double_claim",
    )
    session.expect_code(
        "claim_task",
        {"task_id": f"{project_id}-T999", "agent_identifier": "conformance-probe"},
        "TASK_NOT_FOUND",
        check_id="errors.unknown_task",
    )

    details = session.call("get_task_details", {"task_id": task_id})
    details_payload = details.payload()
    attachment_id: str | None = None
    is_image = False
    if not details.is_error and isinstance(details_payload, dict):
        task = details_payload.get("task")
        if isinstance(task, dict) and task.get("id") == task_id:
            session.ok("details", f"full task payload for {task_id} fetched")
            attachments = task.get("attachments")
            if isinstance(attachments, list) and attachments:
                first = attachments[0]
                if isinstance(first, dict) and first.get("id"):
                    attachment_id = str(first["id"])
                    is_image = first.get("is_image") is True
        else:
            session.record(
                "details",
                "fail",
                f"details payload is not task {task_id}: {details_payload!r:.200}",
            )

    if attachment_id is None:
        report.attachment_skipped = True
        report.add(
            CheckResult(
                "coder.attachment",
                "coder",
                "skip",
                "no attachment on the claimed task - attachment packaging not exercised",
            )
        )
    else:
        outcome.attachment_id = attachment_id
        _exercise_attachment(
            session,
            task_id=task_id,
            attachment_id=attachment_id,
            is_image=is_image,
            capability=capability,
        )

    checkpoint = session.call(
        "log_task_checkpoint",
        {"task_id": task_id, "message": "conformance checkpoint", "percentage": 50},
    )
    checkpoint_payload = checkpoint.payload()
    if not checkpoint.is_error and isinstance(checkpoint_payload, dict):
        inner = checkpoint_payload.get("checkpoint")
        if isinstance(inner, dict) and checkpoint_payload.get("lease_expires_at"):
            session.ok("checkpoint", "checkpoint logged and lease extended")
        else:
            session.record(
                "checkpoint",
                "fail",
                "checkpoint payload missing checkpoint/lease_expires_at: "
                f"{checkpoint_payload!r:.200}",
            )

    branch_name = claim_payload.get("branch")
    if prepare_commit is not None and isinstance(branch_name, str) and branch_name:
        try:
            prepared = prepare_commit(branch_name)
        except (OSError, RuntimeError) as exc:
            session.record("submit.repo", "fail", f"repo preparation for submission failed: {exc}")
            _release_best_effort(session, task_id)
            return outcome
        submit = session.call(
            "submit_task_resolution",
            {
                "task_id": task_id,
                "git_branch": prepared.branch,
                "commit_sha": prepared.sha,
                "execution_summary": "Conformance runner submission (MT-2.11-01).",
            },
        )
        submit_payload = submit.payload()
        if not submit.is_error and isinstance(submit_payload, dict):
            state = submit_payload.get("outcome")
            if state == "to_be_audited":
                outcome.submitted_task_id = task_id
                session.ok("submit", f"{task_id} reached to_be_audited (T7)")
            else:
                session.record(
                    "submit",
                    "fail",
                    f"submission escalated to {state!r} "
                    f"(review_reason={submit_payload.get('review_reason')!r}) - "
                    "expected to_be_audited (T7)",
                )
        _exercise_release_on_second_task(
            report, session, project_id=project_id, held=task_id, outcome=outcome
        )
    else:
        _release_best_effort(session, task_id, outcome=outcome)
    return outcome


def _exercise_release_on_second_task(
    report: ConformanceReport,
    session: RoleSession,
    *,
    project_id: str,
    held: str,
    outcome: CoderOutcome,
) -> None:
    """Claim and voluntarily release a *second* pending task (FR-LEA-06 path)."""
    listing = session.call("get_available_tasks", {"role": "coder"})
    if listing.is_error or listing.payload() is None:
        return
    candidate = next(
        (
            task
            for task in _tasks_of(listing)
            if task.get("state") == "pending" and task.get("id") != held
        ),
        None,
    )
    if candidate is None:
        report.add(
            CheckResult(
                "coder.release",
                "coder",
                "skip",
                f"no second pending task of {project_id} to release",
            )
        )
        return
    task_id = str(candidate["id"])
    claim = session.call(
        "claim_task", {"task_id": task_id, "agent_identifier": "conformance-coder"}
    )
    if claim.is_error or claim.payload() is None:
        return
    _release_best_effort(session, task_id, outcome=outcome)


def _release_best_effort(
    session: RoleSession, task_id: str, *, outcome: CoderOutcome | None = None
) -> None:
    """Return the held task to pending so one failed run does not poison the next."""
    release = session.call("release_task", {"task_id": task_id, "reason": "conformance"})
    release_payload = release.payload()
    if not release.is_error and isinstance(release_payload, dict):
        if release_payload.get("released") is True:
            if outcome is not None:
                outcome.released_task_id = task_id
            session.ok("release", f"{task_id} released back to pending")
        else:
            session.record(
                "release", "fail", f"release payload unexpected: {release_payload!r:.200}"
            )


def _exercise_attachment(
    session: RoleSession,
    *,
    task_id: str,
    attachment_id: str,
    is_image: bool,
    capability: str | None,
) -> None:
    """Both Section 10.4 packagings: vision image blocks vs text + banner."""
    auto = session.call(
        "read_task_attachment",
        {"task_id": task_id, "attachment_id": attachment_id, "format_preference": "auto"},
    )
    if auto.is_error or auto.payload() is None:
        return
    if auto.has_image_block:
        session.report.vision_path_seen = True
        session.ok(
            "attachment.vision",
            "auto read returned an image content block (vision path, FR-ATT-05)",
        )
    else:
        payload = auto.payload()
        text = payload.get("content") if isinstance(payload, dict) else None
        bannered = isinstance(text, str) and text.count(BANNER_MARKER) == 1
        resolution = payload.get("resolution") if isinstance(payload, dict) else None
        has_resolution = isinstance(resolution, dict) and "step" in resolution
        if bannered and has_resolution:
            session.report.text_only_path_seen = True
            session.ok(
                "attachment.text",
                "auto read returned bannered OCR/description text with the "
                "resolution block (text-safe path)",
            )
        else:
            session.record(
                "attachment.text",
                "fail",
                f"text packaging missing single untrusted banner or resolution: {payload!r:.200}",
            )

    text_only = session.call(
        "read_task_attachment",
        {"task_id": task_id, "attachment_id": attachment_id, "format_preference": "text_ocr"},
    )
    payload = text_only.payload()
    if not text_only.is_error and isinstance(payload, dict):
        content = payload.get("content")
        description = payload.get("description")
        content_ok = isinstance(content, str) and content.count(BANNER_MARKER) == 1
        description_ok = description is None or (
            isinstance(description, str) and description.count(BANNER_MARKER) == 1
        )
        if content_ok and description_ok:
            session.ok(
                "attachment.banner",
                "explicit text_ocr read carries the untrusted banner exactly once",
            )
        else:
            session.record(
                "attachment.banner",
                "fail",
                "text_ocr packaging does not carry exactly one untrusted banner",
            )

    # Section 9.5's gate: a *known* text-only session never silently receives
    # an image; an unknown session is text-safe by default but an explicit
    # image request is its own decision (the step-4 note tells it how), so
    # the rejection check runs only for capability == "text_only".
    if is_image and capability == "text_only":
        session.expect_code(
            "read_task_attachment",
            {
                "task_id": task_id,
                "attachment_id": attachment_id,
                "format_preference": "image_base64",
            },
            "ATTACHMENT_UNSUPPORTED_FORMAT",
            check_id="attachment.text_only_gate",
        )
    elif is_image and capability == "vision":
        vision = session.call(
            "read_task_attachment",
            {
                "task_id": task_id,
                "attachment_id": attachment_id,
                "format_preference": "image_base64",
            },
        )
        if vision.is_error or vision.payload() is None:
            return
        if vision.has_image_block:
            session.ok(
                "attachment.vision_explicit",
                "explicit image_base64 read returned an image block for a vision session",
            )
        else:
            session.record(
                "attachment.vision_explicit",
                "fail",
                "vision session got no image block from an explicit image_base64 read",
            )


def run_auditor_scenario(
    report: ConformanceReport,
    session: RoleSession,
    *,
    prefer_task_id: str | None,
    expected_project_rules: str | None = None,
) -> None:
    """The auditor flow: list to_be_audited -> claim -> submit_audit_verdict."""
    assert session.role == "auditor"
    listing = session.call("get_available_tasks", {"role": "auditor"})
    candidate: dict[str, Any] | None = None
    if not listing.is_error and listing.payload() is not None:
        tasks = _tasks_of(listing)
        if prefer_task_id is not None:
            candidate = next(
                (
                    task
                    for task in tasks
                    if task.get("id") == prefer_task_id and task.get("state") == "to_be_audited"
                ),
                None,
            )
        if candidate is None:
            candidate = _pick_task(tasks, state="to_be_audited")
        if candidate is None:
            session.record("list", "fail", "no to_be_audited task in the auditor work list")
    if candidate is None:
        return
    task_id = str(candidate["id"])
    session.ok("list", f"work list offered to_be_audited task {task_id}")

    claim = session.call(
        "claim_task",
        {"task_id": task_id, "agent_identifier": "conformance-auditor", "role": "auditor"},
    )
    claim_payload = claim.payload()
    if claim.is_error or not isinstance(claim_payload, dict):
        return
    session.ok("claim", f"auditor claimed {task_id}")
    rules_text = claim_payload.get("rules")
    check_claim_rules(
        report,
        "auditor",
        rules_text.get("text") if isinstance(rules_text, dict) else None,
        expected_project_rules=expected_project_rules,
    )

    verdict = session.call(
        "submit_audit_verdict",
        {
            "task_id": task_id,
            "verdict": "pass",
            "confidence": 4,
            "notes": "Conformance run audit (MT-2.11-01).",
            "evidence": {
                "commands": [
                    {
                        "label": "conformance probe",
                        "command": "true",
                        "exit_code": 0,
                    }
                ],
                "lint_clean": True,
            },
        },
    )
    verdict_payload = verdict.payload()
    if not verdict.is_error and isinstance(verdict_payload, dict):
        if verdict_payload.get("verdict") == "pass" and isinstance(
            verdict_payload.get("task"), dict
        ):
            session.ok("verdict", f"verdict accepted for {task_id}")
        else:
            session.record(
                "verdict", "fail", f"verdict payload unexpected: {verdict_payload!r:.200}"
            )


def run_decomposer_scenario(report: ConformanceReport, session: RoleSession) -> None:
    """The decomposer flow: create_draft_task only (Section 12.2)."""
    assert session.role == "decomposer"
    draft = session.call(
        "create_draft_task",
        {
            "title": "Conformance draft task (MT-2.11-01)",
            "description": "Created by the MCP conformance runner; safe to delete.",
        },
    )
    payload = draft.payload()
    if not draft.is_error and isinstance(payload, dict):
        if payload.get("state") == "draft" and payload.get("task_id"):
            session.ok("draft", f"draft task {payload['task_id']} created in state draft")
        else:
            session.record("draft", "fail", f"draft payload unexpected: {payload!r:.200}")


def tools_expected() -> tuple[str, ...]:
    """The Section 10.5 catalog the run must exercise (report cross-check)."""
    return CORE_TOOL_NAMES
