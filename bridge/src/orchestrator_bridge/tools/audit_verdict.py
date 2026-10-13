"""``submit_audit_verdict`` (Sections 10.5, 11.2; MT-3.5-01, MT-3.5-02).

The auditor's structured result: the bridge validates the verdict payload
**before** touching the wire, then POSTs it with the session's fencing pair
(``session_id`` + ``lease_generation``). The Policy Engine — not the bridge —
decides the task's final state (Section 10.5; WP-3.4).

MT-3.5-01: the registered input schema is Section 10.5's auditor verdict
shape, field for field (``task_id``/``verdict``/``confidence``/``notes``/
``evidence``/``acceptance_criteria_results``), pinned by a snapshot test.

MT-3.5-02: two validation layers guard the endpoint call:

* the declared schema (validated by ``registration.BridgeTool`` before this
  function runs) covers types, the verdict enum, the 1–5 confidence bounds
  and the required keys;
* :func:`validate_verdict_payload` adds the semantics a schema cannot
  express — at least one command entry, non-empty ``label``/``command``/
  ``criterion`` strings — and every rejection is a ``VALIDATION_ERROR`` whose
  ``next_action`` names the offending field (Section 10.5 error rule).

Valid payloads pass through **unchanged**: ``evidence`` is forwarded
verbatim, including any extra keys the auditor attached (the backend stores
evidence as supplied — FR-AUD-02; the top-level schema is strict so nothing
unexpected sneaks past the documented fields, while nested objects stay
open).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..endpoints import endpoint
from ..error_translation import TranslatedError, translate_error
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["make_handler", "submit_audit_verdict", "validate_verdict_payload"]


def _invalid(field: str, problem: str, action: str) -> ToolFailure:
    """One field-naming VALIDATION_ERROR (Section 10.5 error rule)."""
    return ToolFailure(
        TranslatedError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"invalid audit verdict payload: {problem}",
            hint=f"Field '{field}' {problem}.",
            next_action=action,
            retryable=False,
            details={"field": field},
            correlation_id=None,
        )
    )


def _command_field(entry: object, index: int) -> str:
    """One command entry's semantic check; returns the failing field name."""
    if not isinstance(entry, Mapping):  # pragma: no cover - schema catches it first
        return f"evidence.commands[{index}]"
    label = entry.get("label")
    if not isinstance(label, str) or not label.strip():
        return f"evidence.commands[{index}].label"
    command = entry.get("command")
    if not isinstance(command, str) or not command.strip():
        return f"evidence.commands[{index}].command"
    exit_code = entry.get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        return f"evidence.commands[{index}].exit_code"
    return ""


def validate_verdict_payload(
    *,
    evidence: Mapping[str, Any],
    acceptance_criteria_results: list[Any] | None,
) -> None:
    """Semantic checks beyond the declared schema (MT-3.5-02).

    Raises a field-naming ``VALIDATION_ERROR`` failure; never rewrites the
    payload (evidence must reach the backend exactly as the auditor wrote
    it). The schema already guaranteed the required keys, types, enum and
    bounds; this layer adds what JSON Schema cannot express cleanly.
    """
    commands = evidence.get("commands")
    if not isinstance(commands, list) or not commands:
        raise _invalid(
            "evidence.commands",
            "must list at least one command entry",
            "Add one or more {label, command, exit_code} entries to evidence.commands "
            "and submit the verdict again.",
        )
    for index, entry in enumerate(commands):
        failing = _command_field(entry, index)
        if failing:
            raise _invalid(
                failing,
                "must carry a non-empty string and an integer exit_code",
                f"Fix '{failing}' (non-empty label and command strings, integer "
                "exit_code) and submit the verdict again.",
            )
    if acceptance_criteria_results is not None:
        for index, item in enumerate(acceptance_criteria_results):
            criterion = item.get("criterion") if isinstance(item, Mapping) else None
            if not isinstance(criterion, str) or not criterion.strip():
                raise _invalid(
                    f"acceptance_criteria_results[{index}].criterion",
                    "must be a non-empty string paired with a boolean 'met'",
                    f"Fix acceptance_criteria_results[{index}] (criterion + met) and "
                    "submit the verdict again.",
                )


def submit_audit_verdict(
    runtime: ToolRuntime,
    *,
    task_id: str,
    verdict: str,
    confidence: int,
    evidence: Mapping[str, Any],
    notes: str = "",
    acceptance_criteria_results: list[Any] | None = None,
) -> dict[str, Any]:
    """Validate, then POST the verdict with the session's fencing pair."""
    validate_verdict_payload(
        evidence=evidence, acceptance_criteria_results=acceptance_criteria_results
    )
    body: dict[str, Any] = {
        "session_id": runtime.agent_session_id,
        # ADR-012 fencing pair: the last generation claimed here (0 when the
        # session never claimed this task — the backend answers authoritatively).
        "lease_generation": runtime.lease_generation(task_id) or 0,
        "task_id": task_id,
        "verdict": verdict,
        "confidence": confidence,
        # Verbatim passthrough (FR-AUD-02): evidence is stored as supplied.
        "evidence": dict(evidence),
    }
    if notes:
        body["notes"] = notes
    if acceptance_criteria_results is not None:
        body["acceptance_criteria_results"] = acceptance_criteria_results
    try:
        payload = runtime.client.request(
            "POST", endpoint("audit_verdict").path.format(id=task_id), body=body
        )
    except ApiError as exc:
        raise ToolFailure(translate_error(exc)) from None
    if not isinstance(payload, Mapping):
        raise ToolFailure(
            translate_error(
                ApiError(
                    code=ErrorCode.SERVER_ERROR,
                    message="audit verdict response is not the documented object",
                    retryable=False,
                    kind=ErrorKind.MALFORMED_RESPONSE,
                    details={"endpoint": "audit_verdict"},
                )
            )
        )
    report = payload.get("report")
    task = payload.get("task")
    return {
        "task_id": task_id,
        "verdict": verdict,
        "report": dict(report) if isinstance(report, Mapping) else None,
        "task": dict(task) if isinstance(task, Mapping) else None,
    }


def make_handler(runtime: ToolRuntime) -> Callable[..., dict[str, Any]]:
    """The registered MCP handler: schema-typed arguments, bound session."""

    def submit_audit_verdict_tool(
        task_id: str,
        verdict: str,
        confidence: int,
        evidence: Mapping[str, Any],
        notes: str = "",
        acceptance_criteria_results: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Submit one auditor verdict with structured evidence (Section 10.5)."""
        return submit_audit_verdict(
            runtime,
            task_id=task_id,
            verdict=verdict,
            confidence=confidence,
            evidence=evidence,
            notes=notes,
            acceptance_criteria_results=acceptance_criteria_results,
        )

    return submit_audit_verdict_tool
