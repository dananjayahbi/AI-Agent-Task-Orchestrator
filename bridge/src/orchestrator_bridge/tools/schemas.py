"""Deterministic schemas for the five core tools (parent plan Sections 10.5,
18; FR-MCP-03, NFR-11; MT-2.4-01).

The **public contract** of WP-2.4, modeled from Section 10.5's tool catalog
table by pointer, never re-derived: the exact tool names, their exact inputs,
strict-validation keywords (``additionalProperties: false``, enums, ``limit``
bounds) and the Section 9.2 error codes each tool may surface.

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

_GET_PROJECT_CONTEXT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {},
    "description": "No inputs — the answer is always the bound session's project.",
}


#: Section 10.5's five tools, in the plan's catalog order.
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

#: The exact tool set the MCP server must advertise after WP-2.4 (MT-2.4-07
#: inspector check; ordered per Section 10.5's catalog).
CORE_TOOL_NAMES: Final[tuple[str, ...]] = tuple(spec.name for spec in TOOL_SPECS)
