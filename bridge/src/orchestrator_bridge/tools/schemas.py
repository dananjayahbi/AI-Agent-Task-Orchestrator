"""Deterministic schemas for the registered tools (parent plan Sections 10.5,
18; FR-MCP-03, NFR-11; MT-2.4-01, MT-2.6-01/04).

The **public contract** of WP-2.4 (extended by WP-2.6), modeled from
Section 10.5's tool catalog table by pointer, never re-derived: the exact
tool names, their exact inputs, strict-validation keywords
(``additionalProperties: false``, enums, ``limit`` bounds) and the Section
9.2 error codes each tool may surface.

Design rules enforced here and pinned by ``tests/test_tool_schemas.py``:

* **No ``project_id`` parameter anywhere** — the session is bound at startup
  (Section 10.3; MT-2.4-01 risk note); the schema test scans every property
  name so a "helpful" convenience parameter cannot slip in.
* **Closed error vocabulary** — every code in every ``errors`` tuple must be a
  member of the Section 9.2 catalog (Section 20.4 item 5); the test asserts it
  against :class:`~orchestrator_bridge.api_errors.ErrorCode`.
* **Schemas are the wire contract**: ``registration.BridgeTool`` replaces the
  MCP SDK's signature-derived ``inputSchema`` with these dicts on the server,
  and :mod:`validation` enforces them *before* the SDK's looser model runs —
  one source of truth, no drift between what is advertised and what is
  accepted.

Handlers live next door (one module per tool) and are wired by
``registration.register_tools``; nothing here executes anything.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from ..api_errors import ErrorCode

__all__ = [
    "CORE_TOOL_NAMES",
    "READ_ERRORS",
    "ToolSpec",
    "TOOL_SPECS",
]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """One core tool: wire name, description, input schema, allowed errors."""

    name: str
    description: str
    input_schema: Mapping[str, Any]
    errors: tuple[ErrorCode, ...]


#: Every tool can fail this way (Section 9.2 catalog subset; MT-2.3-04 hints).
READ_ERRORS: Final[tuple[ErrorCode, ...]] = (
    ErrorCode.AUTH_REQUIRED,
    ErrorCode.AUTH_FORBIDDEN_PROJECT,
    ErrorCode.VALIDATION_ERROR,
    ErrorCode.RATE_LIMITED,
    ErrorCode.SERVER_ERROR,
)

_ROLE_ENUM: Final[list[str]] = ["coder", "auditor"]
_PRIORITY_ENUM: Final[list[str]] = ["urgent", "high", "medium", "low"]

_GET_AVAILABLE_TASKS_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "priority_filter": {
            "type": "string",
            "enum": _PRIORITY_ENUM,
            "description": "FR-TSK-05 priority filter (single value; omit for all).",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "default": 25,
            "description": "Maximum descriptors to return (backend page cap is 100).",
        },
        "role": {
            "type": "string",
            "enum": _ROLE_ENUM,
            "default": "coder",
            "description": "coder → pending, unblocked work; auditor → to_be_audited.",
        },
    },
}

_GET_TASK_DETAILS_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "task_id": {
            "type": "string",
            "minLength": 1,
            "description": "Task id ({PID}-T{index}, Section 7.3) inside the bound project.",
        },
    },
    "required": ["task_id"],
}

_CLAIM_TASK_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "task_id": {
            "type": "string",
            "minLength": 1,
            "description": "Task id to claim atomically (Section 9.3).",
        },
        "agent_identifier": {
            "type": "string",
            "minLength": 1,
            "maxLength": 255,
            "description": "Human-readable worker label (self-declared; G-18).",
        },
        "role": {
            "type": "string",
            "enum": _ROLE_ENUM,
            "default": "coder",
            "description": (
                "Claiming role (Section 12.2). The backend derives what each "
                "token role may claim from the token's scopes; the wire body "
                "carries no role field (ClaimRequest contract)."
            ),
        },
    },
    "required": ["task_id", "agent_identifier"],
}

_READ_TASK_ATTACHMENT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "task_id": {
            "type": "string",
            "minLength": 1,
            "description": "Task id whose attachment is read (Section 10.5).",
        },
        "attachment_id": {
            "type": "string",
            "minLength": 1,
            "description": "Attachment id from the task's descriptor (Section 9.5).",
        },
        "format_preference": {
            "type": "string",
            "enum": ["auto", "image_base64", "text_ocr", "markdown"],
            "default": "auto",
            "description": (
                "auto resolves per Section 10.4 (explicit values win over the session "
                "capability, client table and text-safe default)."
            ),
        },
        "page_number": {
            "type": "integer",
            "minimum": 1,
            "default": 1,
            "description": (
                "One-based page for paginated documents (Section 9.5); a documented "
                "no-op on the image/OCR paths."
            ),
        },
        "force": {
            "type": "boolean",
            "default": False,
            "description": (
                "Override the text-only gate for an explicit image_base64 request "
                "(Section 9.5 'unless forced'); never needed for auto/text_ocr/markdown."
            ),
        },
    },
    "required": ["task_id", "attachment_id"],
}

_RELEASE_TASK_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "task_id": {
            "type": "string",
            "minLength": 1,
            "description": "Task id to release back to pending (voluntarily).",
        },
        "reason": {
            "type": "string",
            "maxLength": 500,
            "default": "",
            "description": "Free-text reason recorded on the transition (Section 10.5).",
        },
    },
    "required": ["task_id"],
}

_SUBMIT_AUDIT_VERDICT_COMMAND_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    # Open (FR-AUD-02): the backend stores evidence entries as supplied —
    # extra keys (durations, diff stats) pass through verbatim.
    "additionalProperties": True,
    "properties": {
        "label": {"type": "string"},
        "command": {"type": "string"},
        "exit_code": {"type": "integer"},
        "summary": {"type": "string"},
    },
    "required": ["label", "command", "exit_code"],
}

_SUBMIT_AUDIT_VERDICT_CRITERION_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "criterion": {"type": "string"},
        "met": {"type": "boolean"},
    },
    "required": ["criterion", "met"],
}

#: Section 10.5's auditor verdict shape, field for field (MT-3.5-01 snapshot
#: test). Top level is strict (tool design rule: nothing beyond the
#: documented fields — never a project id); nested evidence stays open so
#: auditor-supplied keys survive verbatim (FR-AUD-02).
_SUBMIT_AUDIT_VERDICT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "task_id": {
            "type": "string",
            "minLength": 1,
            "description": "Audited task id (Section 10.5).",
        },
        "verdict": {
            "type": "string",
            "enum": ["pass", "flag_risk", "fail"],
            "description": (
                "Auditor's structured result; the Policy Engine decides the final state."
            ),
        },
        "confidence": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "Honest confidence 1–5 (rules: report it truthfully).",
        },
        "notes": {
            "type": "string",
            "description": "Optional auditor notes alongside the structured evidence.",
        },
        "evidence": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "commands": {
                    "type": "array",
                    "items": _SUBMIT_AUDIT_VERDICT_COMMAND_SCHEMA,
                },
                "lint_clean": {"type": "boolean"},
            },
            "required": ["commands"],
            "description": "Real command results (label/command/exit_code) plus lint state.",
        },
        "acceptance_criteria_results": {
            "type": "array",
            "items": _SUBMIT_AUDIT_VERDICT_CRITERION_SCHEMA,
            "description": "One {criterion, met} pair per acceptance criterion reviewed.",
        },
    },
    "required": ["task_id", "verdict", "confidence", "evidence"],
}

_GET_PROJECT_CONTEXT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {},
    "description": "No inputs — the answer is always the bound session's project.",
}

_LOG_TASK_CHECKPOINT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "task_id": {
            "type": "string",
            "minLength": 1,
            "description": "Held task to report progress on (Section 10.5).",
        },
        "message": {
            "type": "string",
            "default": "",
            "description": "The agent's free-text progress report (Section 7.2).",
        },
        "percentage": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Optional 0-100 completion hint (Section 7.2 bounds).",
        },
    },
    "required": ["task_id"],
}

_SUBMIT_TASK_RESOLUTION_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "task_id": {
            "type": "string",
            "minLength": 1,
            "description": "Held task to finish (Section 10.5).",
        },
        "git_branch": {
            "type": "string",
            "minLength": 1,
            "maxLength": 255,
            "description": (
                "Branch the work was committed on — must be the task's assigned "
                "branch (G-09; the bridge verifies it)."
            ),
        },
        "commit_sha": {
            "type": "string",
            "minLength": 4,
            "maxLength": 64,
            "description": (
                "Commit the submission points at — must resolve and be reachable "
                "on the assigned branch (the bridge verifies it)."
            ),
        },
        "execution_summary": {
            "type": "string",
            "description": (
                "The coder's summary of what was done and which tests ran (rules items 3 and 8)."
            ),
        },
        "requires_human_attention": {
            "type": "boolean",
            "default": False,
            "description": (
                "Self-flag: routes the submission to human review (T8, "
                "review_reason self_flagged) instead of straight audit."
            ),
        },
        "risk_justification": {
            "type": "string",
            "default": "",
            "description": "Why the coder is flagging the submission (Section 7.2).",
        },
    },
    "required": ["task_id", "git_branch", "commit_sha", "execution_summary"],
}


#: Section 10.5's tools, in the plan's catalog order (WP-2.4's five core
#: plus WP-2.6's checkpoint/submission pair, which the plan lists between
#: claim and release; read_task_attachment lands with WP-2.5).
TOOL_SPECS: Final[tuple[ToolSpec, ...]] = (
    ToolSpec(
        name="get_available_tasks",
        description=(
            "List the bound project's offerable tasks for the given role "
            "(Section 10.5): coders see pending, unblocked work; auditors see "
            "tasks awaiting audit. Returns compact descriptors — never "
            "attachment content (fetch attachments on demand instead)."
        ),
        input_schema=_GET_AVAILABLE_TASKS_SCHEMA,
        errors=(*READ_ERRORS, ErrorCode.ROLE_NOT_PERMITTED),
    ),
    ToolSpec(
        name="get_task_details",
        description=(
            "Full payload for one task of the bound project (Section 10.5): "
            "description, acceptance criteria, target scope, test command, "
            "state, lease/dependency status and feedback from previous "
            "attempts; resolution info when the backend returns it."
        ),
        input_schema=_GET_TASK_DETAILS_SCHEMA,
        errors=(*READ_ERRORS, ErrorCode.TASK_NOT_FOUND),
    ),
    ToolSpec(
        name="claim_task",
        description=(
            "Atomically claim one task of the bound project (Section 9.3 — "
            "exactly one claimant wins). Returns the lease record, the "
            "Section 10.6 rules block and the canonical branch name. Create "
            "and switch to that branch before editing."
        ),
        input_schema=_CLAIM_TASK_SCHEMA,
        errors=(
            *READ_ERRORS,
            ErrorCode.TASK_NOT_FOUND,
            ErrorCode.TASK_STATE_CONFLICT,
            ErrorCode.TASK_ALREADY_CLAIMED,
            ErrorCode.DEPENDENCY_UNMET,
            ErrorCode.CONCURRENCY_LIMIT_REACHED,
            ErrorCode.ROLE_NOT_PERMITTED,
            ErrorCode.AUDITOR_SAME_AS_CODER,
        ),
    ),
    ToolSpec(
        name="read_task_attachment",
        description=(
            "Read one task attachment with capability negotiation (Sections 9.5, "
            "10.4): images become MCP image blocks for vision sessions; every other "
            "session gets OCR text plus a description with the untrusted banner. "
            "Documents paginate one-based (page_number). Every result reports which "
            "resolution step decided (explicit format, session config, client table "
            "or text-safe default) — the bridge never claims vision the client "
            "lacks (ADR-006)."
        ),
        input_schema=_READ_TASK_ATTACHMENT_SCHEMA,
        errors=(
            *READ_ERRORS,
            ErrorCode.TASK_NOT_FOUND,
            ErrorCode.ATTACHMENT_NOT_READY,
            ErrorCode.ATTACHMENT_UNSUPPORTED_FORMAT,
        ),
    ),
    ToolSpec(
        name="log_task_checkpoint",
        description=(
            "Report progress on a held task and extend its lease (Section 10.5; "
            "rule 5). Returns the new lease expiry plus the next_checkpoint_due "
            "hint (RISK-02). A LEASE_EXPIRED answer means stop immediately and "
            "re-claim — never keep working on a dead lease."
        ),
        input_schema=_LOG_TASK_CHECKPOINT_SCHEMA,
        errors=(
            *READ_ERRORS,
            ErrorCode.TASK_NOT_FOUND,
            ErrorCode.TASK_STATE_CONFLICT,
            ErrorCode.LEASE_EXPIRED,
            ErrorCode.LEASE_NOT_OWNED,
        ),
    ),
    ToolSpec(
        name="submit_task_resolution",
        description=(
            "Finish coder work on a held task (Section 10.5): the bridge verifies "
            "the assigned branch and commit sha host-side, captures the merge-base "
            "patch with its file list (Section 9.7), retains the payload locally "
            "and uploads it with an idempotency key. Reports the actual outcome — "
            "to_be_audited (T7) or in_human_review with its review_reason (T8)."
        ),
        input_schema=_SUBMIT_TASK_RESOLUTION_SCHEMA,
        errors=(
            *READ_ERRORS,
            ErrorCode.TASK_NOT_FOUND,
            ErrorCode.TASK_STATE_CONFLICT,
            ErrorCode.LEASE_EXPIRED,
            ErrorCode.LEASE_NOT_OWNED,
            ErrorCode.SCOPE_VIOLATION,
            ErrorCode.ROLE_NOT_PERMITTED,
        ),
    ),
    ToolSpec(
        name="release_task",
        description=(
            "Voluntarily return a held task to pending (Section 10.5). No "
            "failure attempt is consumed (FR-LEA-06): releasing is not a "
            "failed claim. Use it when the work must stop (e.g. a scope "
            "expansion is truly needed) instead of abandoning the lease."
        ),
        input_schema=_RELEASE_TASK_SCHEMA,
        errors=(
            *READ_ERRORS,
            ErrorCode.TASK_NOT_FOUND,
            ErrorCode.TASK_STATE_CONFLICT,
            ErrorCode.LEASE_NOT_OWNED,
            ErrorCode.LEASE_EXPIRED,
        ),
    ),
    ToolSpec(
        name="submit_audit_verdict",
        description=(
            "Submit one auditor verdict for a held task (Sections 10.5, 11.2): the "
            "structured pass/flag_risk/fail result with confidence, real command "
            "evidence (label, command, exit_code) and per-criterion results. The "
            "bridge validates the payload before the call and forwards evidence "
            "verbatim; the Policy Engine decides the task's final state."
        ),
        input_schema=_SUBMIT_AUDIT_VERDICT_SCHEMA,
        errors=(
            *READ_ERRORS,
            ErrorCode.TASK_NOT_FOUND,
            ErrorCode.TASK_STATE_CONFLICT,
            ErrorCode.LEASE_EXPIRED,
            ErrorCode.LEASE_NOT_OWNED,
            ErrorCode.ROLE_NOT_PERMITTED,
            ErrorCode.AUDITOR_SAME_AS_CODER,
        ),
    ),
    ToolSpec(
        name="get_project_context",
        description=(
            "Cheap orientation (Section 10.5): the bound project's name, "
            "rules and policy summary from the session cache — no backend "
            "round trip once cached (Section 10.3 step 5). Call it first "
            "after connecting."
        ),
        input_schema=_GET_PROJECT_CONTEXT_SCHEMA,
        errors=READ_ERRORS,
    ),
)

#: The exact tool set the MCP server must advertise (MT-2.4-07 inspector
#: check, extended by WP-2.6's checkpoint/submission pair; ordered per
#: Section 10.5's catalog).
CORE_TOOL_NAMES: Final[tuple[str, ...]] = tuple(spec.name for spec in TOOL_SPECS)
