"""Individual conformance checks (MT-2.11-01; Sections 10.5, 10.6, 10.7, 9.2).

Each check is one recorded :class:`~tests.conformance.report.CheckResult`:

* the advertised tool catalog equals Section 10.5's ten tools with their
  declared schemas (a client-visible contract break fails the run);
* the Section 10.6 rules block reaches the client at both channels —
  ``initialize`` instructions and the ``claim_task`` result (FR-MCP-05);
* the four Section 10.7 prompts surface via ``prompts/list`` and render via
  ``prompts/get`` — *absence is reported, not failed* (NFR-08 / MT-2.11-01);
* every structured error code observed on the wire is a member of the
  Section 9.2 catalog (``api_errors.ErrorCode``), never an invented code.
"""

from __future__ import annotations

from typing import Any

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.prompts import PROMPT_NAMES
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES, TOOL_SPECS

from .report import CheckResult, ConformanceReport

__all__ = [
    "BANNER_MARKER",
    "KNOWN_ERROR_CODES",
    "check_error_catalog",
    "check_initialize_rules",
    "check_claim_rules",
    "check_prompt_render",
    "check_prompts",
    "check_tool_catalog",
]

#: The marker every untrusted attachment text carries (Section 9.5; P10).
BANNER_MARKER = "[UNTRUSTED CONTENT]"

#: The complete Section 9.2 error-code catalog — no invented code passes.
KNOWN_ERROR_CODES: frozenset[str] = frozenset(code.value for code in ErrorCode)

_RULES_HEADER_MARKERS = ("Section 10.6", "Project rules:")


def check_tool_catalog(report: ConformanceReport, role: str, tools: list[dict[str, Any]]) -> None:
    """The advertised tool set is exactly Section 10.5's catalog, schemas included.

    Registration pins ``tool.parameters`` to the declared input schema
    (``tools/registration.py``), so a schema mismatch on the wire is a real
    contract break — the same drift the inspector checks in MT-2.4-07.
    """
    advertised = [str(tool.get("name", "")) for tool in tools]
    if sorted(advertised) != sorted(CORE_TOOL_NAMES):
        report.add(
            CheckResult(
                f"{role}.catalog.tools",
                role,
                "fail",
                f"tools/list advertised {advertised}, expected the "
                f"{len(CORE_TOOL_NAMES)} Section 10.5 tools {list(CORE_TOOL_NAMES)}",
            )
        )
        return
    spec_by_name = {spec.name: spec for spec in TOOL_SPECS}
    schema_mismatches = [
        name
        for name in advertised
        if tool_schema(tools, name) != dict(spec_by_name[name].input_schema)
    ]
    if schema_mismatches:
        report.add(
            CheckResult(
                f"{role}.catalog.schemas",
                role,
                "fail",
                f"input schemas differ from the declared contract: {schema_mismatches}",
            )
        )
        return
    report.add(
        CheckResult(
            f"{role}.catalog",
            role,
            "pass",
            f"{len(advertised)} tools with declared input schemas (Section 10.5)",
        )
    )


def tool_schema(tools: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """The advertised input schema of one tool (``inputSchema`` on the wire)."""
    for tool in tools:
        if tool.get("name") == name:
            schema = tool.get("inputSchema")
            return dict(schema) if isinstance(schema, dict) else {}
    return {}


def check_initialize_rules(report: ConformanceReport, instructions: Any) -> None:
    """FR-MCP-05 channel 1: the rules block arrives in ``initialize`` instructions."""
    text = instructions if isinstance(instructions, str) else ""
    missing = [marker for marker in _RULES_HEADER_MARKERS if marker not in text]
    if missing:
        report.add(
            CheckResult(
                "connect.rules.initialize",
                "connect",
                "fail",
                f"initialize instructions missing {missing} "
                "(Section 10.6 rules block not delivered, FR-MCP-05)",
            )
        )
        return
    report.add(
        CheckResult(
            "connect.rules.initialize",
            "connect",
            "pass",
            "initialize instructions carry the coder Section 10.6 block with project rules",
        )
    )


def check_claim_rules(
    report: ConformanceReport,
    role: str,
    rules_text: Any,
    *,
    expected_project_rules: str | None = None,
) -> None:
    """FR-MCP-05 channel 2: the claim result carries the role's rules block."""
    text = rules_text if isinstance(rules_text, str) else ""
    role_header = "Coder rules" if role == "coder" else "Auditor rules"
    missing = [marker for marker in (role_header, *_RULES_HEADER_MARKERS) if marker not in text]
    if expected_project_rules and expected_project_rules not in text:
        missing.append(f"project rules {expected_project_rules!r}")
    if missing:
        report.add(
            CheckResult(
                f"{role}.claim.rules",
                role,
                "fail",
                f"claim rules block missing {missing} (Section 10.6, FR-MCP-05)",
            )
        )
        return
    report.add(
        CheckResult(
            f"{role}.claim.rules",
            role,
            "pass",
            f"claim delivered the {role} Section 10.6 block with project rules appended",
        )
    )


def check_prompts(report: ConformanceReport, prompts: list[dict[str, Any]]) -> list[str]:
    """Record which of the four Section 10.7 prompts surfaced (reported, not failed).

    Returns the surfaced names so the caller can render each one.
    """
    advertised = {str(prompt.get("name", "")) for prompt in prompts if isinstance(prompt, dict)}
    surfaced = [name for name in PROMPT_NAMES if name in advertised]
    absent = [name for name in PROMPT_NAMES if name not in advertised]
    report.prompts_surfaced = surfaced
    report.prompts_absent = absent
    unexpected = sorted(advertised - set(PROMPT_NAMES))
    detail = (
        f"{len(surfaced)} of {len(PROMPT_NAMES)} Section 10.7 prompts surfaced"
        + (f"; absent: {absent}" if absent else "")
        + (f"; unexpected extras: {unexpected}" if unexpected else "")
        + " — absence is reported, not failed (NFR-08 / MT-2.11-01)"
    )
    report.add(CheckResult("connect.prompts", "connect", "reported", detail))
    return surfaced


def check_prompt_render(
    report: ConformanceReport, name: str, result: Any, *, error: str | None = None
) -> None:
    """``prompts/get`` renders one surfaced prompt to non-empty message text."""
    check_id = f"connect.prompt.{name}"
    if error is not None:
        report.prompt_render_failures.append(name)
        report.add(CheckResult(check_id, "connect", "fail", f"prompts/get failed: {error}"))
        return
    messages = result.get("messages") if isinstance(result, dict) else None
    texts = [
        block.get("content", {}).get("text", "")
        for block in (messages or [])
        if isinstance(block, dict) and isinstance(block.get("content"), dict)
    ]
    if not any(isinstance(text, str) and text.strip() for text in texts):
        report.prompt_render_failures.append(name)
        report.add(CheckResult(check_id, "connect", "fail", "prompt rendered no text messages"))
        return
    report.add(
        CheckResult(check_id, "connect", "pass", f"rendered {len(texts)} message(s) with text")
    )


def check_error_catalog(report: ConformanceReport) -> None:
    """Every code observed on the wire is a Section 9.2 catalog member."""
    unknown = [code for code in report.observed_error_codes if code not in KNOWN_ERROR_CODES]
    if unknown:
        report.add(
            CheckResult(
                "errors.catalog",
                "all",
                "fail",
                f"error codes outside the Section 9.2 catalog: {unknown}",
            )
        )
        return
    observed = report.observed_error_codes
    detail = (
        f"{len(observed)} observed code(s) all from the Section 9.2 catalog: {observed}"
        if observed
        else "no structured errors observed (all observed codes would be catalog members)"
    )
    report.add(CheckResult("errors.catalog", "all", "pass", detail))
