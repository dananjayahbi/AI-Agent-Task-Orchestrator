"""WP-2.8 — the four Section 10.7 prompts (FR-MCP-04, NFR-08; ADR-011).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.8-mcp-prompts/
MT-2.8-01…04 (parent plan Sections 10.7, 10.5, 10.6, 11.1, 11.2, 9.4, 12.1,
19, 20.4, 20.5). One test file for the registry-level invariants plus the
per-prompt step chains, in the MT order the series delivered them.

The inspector-equivalent wire evidence (``prompts/list`` + ``prompts/get``
over a real stdio process) lives in ``test_entrypoints.py``'s handshake
test extension; these tests pin the contract in-process so any drift fails
CI regardless of Node tooling availability (MT-2.8-01 risk note: the listing
assertion is authoritative, not any one client).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from mcp.server.mcpserver.prompts import Prompt
from mcp.types import GetPromptResult

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.prompts import PROMPT_NAMES, PROMPT_SPECS, build_prompts
from orchestrator_bridge.server import create_server
from orchestrator_bridge.tools.runtime import ToolRuntime
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES
from tests.conftest import StubHttpBackend, build_settings

BRIDGE_ROOT = Path(__file__).resolve().parent.parent

# --- registry shape (Section 10.7 catalog, MT order) ---------------------------


def test_prompts_list_returns_the_four_plan_prompts_in_order(runtime: ToolRuntime) -> None:
    server = create_server(build_settings(), runtime=runtime)
    listed = asyncio.run(server.list_prompts())
    assert [prompt.name for prompt in listed] == list(PROMPT_NAMES)
    assert PROMPT_NAMES == (
        "orchestrator:start_work",
        "orchestrator:checkpoint",
        "orchestrator:submit_for_audit",
        "orchestrator:audit",
    )


def test_every_prompt_has_a_description_and_no_arguments() -> None:
    # The plan defines no prompt arguments (MT-2.8-01 risk note) — none invented.
    for spec in PROMPT_SPECS:
        assert spec.description.strip(), f"{spec.name} has no description"
        assert spec.text.strip(), f"{spec.name} has no text"
    for prompt in build_prompts():
        assert isinstance(prompt, Prompt)
        assert prompt.arguments is None or prompt.arguments == []


def test_unbound_server_advertises_no_prompts() -> None:
    """WP-2.1 skeleton contract survives: no runtime, no prompts (ADR-011)."""
    server = create_server(build_settings())
    assert asyncio.run(server.list_prompts()) == []


# --- per-prompt step chains (each MT's acceptance) ------------------------------


def _rendered(runtime: ToolRuntime, name: str) -> str:
    server = create_server(build_settings(), runtime=runtime)
    result = asyncio.run(server.get_prompt(name))
    assert isinstance(result, GetPromptResult), f"{name}: multi-round-trip answer has no text"
    parts: list[str] = []
    for message in result.messages:
        content = message.content
        text = getattr(content, "text", None)
        assert isinstance(text, str), f"{name}: non-text prompt content"
        parts.append(text)
    return "\n".join(parts)


def _in_order(text: str, *phrases: str) -> None:
    position = -1
    for phrase in phrases:
        found = text.find(phrase, position + 1)
        assert found > position, f"missing or out of order: {phrase!r}"
        position = found


def test_start_work_walks_the_five_section_10_7_steps_in_order(
    runtime: ToolRuntime,
) -> None:
    text = _rendered(runtime, "orchestrator:start_work")
    _in_order(
        text,
        "get_project_context",
        "get_available_tasks",
        "claim_task",
        "branch name",
        "get_task_details",
        "read_task_attachment",
    )
    # Stop-and-reorient rule (Section 11.1 step 7) and rules-block pointer.
    _in_order(text, "rules block", "LEASE_EXPIRED", "stop and re-orient")
    # Claim errors named in MT-2.8-01's scope (Section 9.2 codes only).
    for code in ("TASK_ALREADY_CLAIMED", "DEPENDENCY_UNMET", "CONCURRENCY_LIMIT_REACHED"):
        assert code in text
    # Pure enhancement: the text must not read as mandatory (RISK-01).
    assert "Optional guidance" in text
    assert "available from the tool" in text


def test_checkpoint_commits_then_logs_and_stops_on_lease_expired(
    runtime: ToolRuntime,
) -> None:
    text = _rendered(runtime, "orchestrator:checkpoint")
    _in_order(text, "Commit current work", "log_task_checkpoint")
    # The next-due hint and the Section 8.6 stop rule, no invented semantics.
    _in_order(text, "next_checkpoint_due", "LEASE_EXPIRED", "never attempt to resurrect")
    assert "lease hard cap" in text
    assert "Optional guidance" in text


def test_submit_for_audit_walks_verify_summarize_submit_in_order(
    runtime: ToolRuntime,
) -> None:
    text = _rendered(runtime, "orchestrator:submit_for_audit")
    _in_order(text, "Run verification", "Summarize", "submit_task_resolution")
    # Honest risk flag (Section 11.1 step 6) and the sha/branch inputs.
    _in_order(text, "git_branch", "commit_sha", "requires_human_attention", "risk_justification")
    # Outcome states remain the backend's decision (T7/T8; Section 9.4).
    _in_order(text, "backend's decision", "to_be_audited", "in_human_review")
    _in_order(text, "LEASE_EXPIRED", "TASK_STATE_CONFLICT", "stop")
    assert "Optional guidance" in text


def test_audit_walks_five_steps_with_independence_and_backend_outcome(
    runtime: ToolRuntime,
) -> None:
    text = _rendered(runtime, "orchestrator:audit")
    _in_order(
        text,
        "get_available_tasks",
        "claim_task",
        "read-only",
        "matrix",
        "Review the diff",
        "submit_audit_verdict",
    )
    # Independence per Section 12.1 (MT-2.8-04 scope).
    _in_order(text, "different session", "AUDITOR_SAME_AS_CODER")
    # Section 10.5 verdict vocabulary, nothing invented (Section 20.5).
    _in_order(text, "pass", "flag_risk", "fail", "confidence 1-5")
    # The backend decides, not the verdict (Section 9.4; ADR-009).
    _in_order(text, "verdict is input", "Policy Engine")
    assert "never modify" in text
    assert "Optional guidance" in text


# --- vocabulary discipline (Sections 10.5 / 9.2; Section 20.4 item 5) ----------

_TOOL_LIKE = re.compile(r"\b[a-z][a-z0-9]+(?:_[a-z0-9]+)+\b")
_CODE_LIKE = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")

#: Snake-case identifiers in the prompt texts that legitimately name tools
#: (Section 10.5) rather than an invented capability.
_KNOWN_TOOLS = {
    "get_project_context",
    "get_available_tasks",
    "claim_task",
    "get_task_details",
    "read_task_attachment",
    "log_task_checkpoint",
    "submit_task_resolution",
    "submit_audit_verdict",
}

#: Non-tool snake-case identifiers, each traceable to a plan section:
#: tool inputs/response fields from Section 10.5, task fields from
#: Section 7.2, and the T7/T8 outcome states from Section 8.2. A token
#: outside this set and _KNOWN_TOOLS is an invented name (Section 20.5).
_KNOWN_FIELDS = {
    "commit_sha",  # 10.5 submit_task_resolution input
    "execution_summary",  # 10.5 submit_task_resolution input
    "exit_code",  # 10.5 verdict evidence field
    "flag_risk",  # 10.5 verdict enum value
    "git_branch",  # 10.5 submit_task_resolution input
    "in_human_review",  # 8.2 T8 outcome state
    "next_action",  # 10.5 tool design rule (every error/response hint)
    "next_checkpoint_due",  # WP-2.6 checkpoint response hint (RISK-02)
    "requires_human_attention",  # 10.5 submit_task_resolution input
    "risk_justification",  # 10.5 submit_task_resolution input
    "target_scope",  # 7.2 task field
    "to_be_audited",  # 8.2 T7 outcome state
}


def test_prompt_texts_name_only_existing_tools_and_catalog_codes() -> None:
    """Every tool-like name is a registered tool or a documented field;
    every code-like name is a Section 9.2 catalog code (Section 20.4
    item 5, 20.5)."""
    catalog = {code.value for code in ErrorCode}
    for spec in PROMPT_SPECS:
        for token in _TOOL_LIKE.findall(spec.text):
            assert token in _KNOWN_TOOLS | _KNOWN_FIELDS, (
                f"{spec.name}: unknown tool-like token {token!r}"
            )
        for token in _CODE_LIKE.findall(spec.text):
            assert token in catalog, f"{spec.name}: {token!r} is not in the Section 9.2 catalog"


def test_registered_tool_names_still_advertised_with_prompts_present(
    runtime: ToolRuntime,
) -> None:
    """ADR-011: prompts ride alongside the identical tool surface."""
    server = create_server(build_settings(), runtime=runtime)
    tools = asyncio.run(server.list_tools())
    assert [tool.name for tool in tools] == list(CORE_TOOL_NAMES)
    assert len(asyncio.run(server.list_prompts())) == len(PROMPT_NAMES)


# --- WP-2.8 inspector acceptance over the real wire (Section 19) ---------------


def test_stdio_process_lists_and_renders_all_four_prompts(
    stub_manifest_env: dict[str, str], stub_http_backend: StubHttpBackend, tmp_path: Path
) -> None:
    """Inspector-equivalent proof: ``prompts/list`` + ``prompts/get`` over
    a real stdio JSON-RPC process (Section 19 WP-2.8 acceptance — each
    prompt lists and renders). The session binds through the stub backend
    exactly like the tools handshake (WP-2.2 Section 10.3 steps 1–5)."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("ORCHESTRATOR_")}
    env.update(stub_manifest_env)
    env["ORCHESTRATOR_SPOOL_DIR"] = str(tmp_path / "spool")
    calls: list[dict[str, object]] = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "wp-2-8-test", "version": "1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "prompts/list", "params": {}},
    ]
    for index, name in enumerate(PROMPT_NAMES, start=3):
        calls.append(
            {"jsonrpc": "2.0", "id": index, "method": "prompts/get", "params": {"name": name}}
        )
    messages = "\n".join(json.dumps(call) for call in calls)
    proc = subprocess.Popen(
        [sys.executable, "-m", "orchestrator_bridge"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=BRIDGE_ROOT,
    )
    stdin = proc.stdin
    stdout = proc.stdout
    stderr_pipe = proc.stderr
    assert stdin is not None and stdout is not None and stderr_pipe is not None
    watchdog = threading.Timer(60.0, proc.kill)
    watchdog.start()
    last_id = 2 + len(PROMPT_NAMES)
    try:
        stdin.write(messages + "\n")
        stdin.flush()
        rpc_lines: list[str] = []
        seen: set[int] = set()
        for line in stdout:
            if not line.strip():
                continue
            rpc_lines.append(line)
            message = json.loads(line)
            if message.get("id") == last_id:
                break
            if message.get("id") is not None:
                seen.add(int(message["id"]))
        stdin.close()
    except BaseException:
        proc.kill()
        raise
    finally:
        watchdog.cancel()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=15)
    tail = stdout.read() or ""
    stderr = stderr_pipe.read() or ""
    all_lines = [line for line in (*rpc_lines, *tail.splitlines()) if line.strip()]
    if len(seen) < last_id - 1 and not any(
        json.loads(line).get("id") == last_id for line in all_lines
    ):
        pytest.fail(
            f"prompt RPC never answered (exit={proc.returncode}); "
            f"stdout={rpc_lines + tail.splitlines()!r}; stderr={stderr}"
        )

    rpc_messages = [json.loads(line) for line in (*rpc_lines, *tail.splitlines()) if line.strip()]
    assert all(message.get("jsonrpc") == "2.0" for message in rpc_messages)

    listed = next(message for message in rpc_messages if message.get("id") == 2)
    advertised = [prompt["name"] for prompt in listed["result"]["prompts"]]
    assert advertised == list(PROMPT_NAMES)  # the registered set, no more
    by_name = {prompt["name"]: prompt for prompt in listed["result"]["prompts"]}
    for spec in PROMPT_SPECS:
        assert by_name[spec.name]["description"] == spec.description
        assert by_name[spec.name].get("arguments") in (None, [], {})

    for offset, spec in enumerate(PROMPT_SPECS, start=3):
        rendered = next(message for message in rpc_messages if message.get("id") == offset)
        texts = [
            block["content"]["text"]
            for block in rendered["result"]["messages"]
            if block.get("content", {}).get("type") == "text"
        ]
        assert spec.text in texts  # the exact registered text renders
