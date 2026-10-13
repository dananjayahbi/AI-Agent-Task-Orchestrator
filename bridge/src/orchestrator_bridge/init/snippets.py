"""Per-client MCP registration snippets (FR-MCP-08 fourth output; Section 10.9; MT-2.12-04).

Printed by ``orchestrator init`` *after a passing self-test only* (the safe
ordering: a snippet for an unbound repo wastes the user's time). One block
per client of the Section 10.9 compatibility matrix — the same client list
WP-2.7's fallback snippets use (:data:`orchestrator_bridge.rules.CLIENT_MATRIX`
is the single source, Section 19.6), each showing how to register **the one
stdio server entry** (FR-MCP-01; Section 10.2 launch model):

* the command resolves to this machine's install: the
  ``orchestrator-bridge-stdio`` console script when it is on ``PATH``,
  else ``python -m orchestrator_bridge --mode stdio`` — machine-generated,
  ephemeral terminal output, never committed (Section 20.4's spirit);
* every block is **secret-free** (FR-SEC-04 applies to generated text): the
  token comes from the user-level config the bridge reads itself
  (Section 10.3 step 3) or ``ORCHESTRATOR_AGENT_TOKEN`` — clients never see
  it; each block names that source;
* every block carries a verification pointer — ``orchestrator init
  --self-test`` (MT-2.12-03) or the bridge under an MCP inspector
  (MT-2.1-04's acceptance flow).

Config syntax is what the plan can assert today: the widely documented
``mcpServers`` registration shape, marked as unverified per client until
WP-2.11's conformance work (Section 10.9 is titled "to be verified in
WP-2.11"); Aider gets a wrapper command line because the matrix lists
"STDIO or wrapper" with no native registration key. HTTP-mode snippets are
WP-2.10/2.11 territory (recorded in the changelog).
"""

from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from ..rules import CLIENT_MATRIX

__all__ = ["ClientRegistration", "bridge_command", "render_snippets"]

_STDIO_SCRIPT: Final = "orchestrator-bridge-stdio"
_SELF_TEST_POINTER: Final = "orchestrator init --self-test"


@dataclass(frozen=True, slots=True)
class ClientRegistration:
    """One Section 10.9 client: matrix cells plus the snippet's block style."""

    label: str
    transport: str  # the matrix's Transport cell, verbatim
    target: str  # where the block goes (client-documented; unverified)
    note: str  # client-specific caveat printed with the block
    style: Literal["json", "command"] = "json"


_CLIENT_REGISTRATIONS: Final[tuple[ClientRegistration, ...]] = (
    ClientRegistration(
        label="Claude Code CLI",
        transport="STDIO",
        target="the project or user MCP config (the `mcpServers` entry)",
        note="reference client (Section 10.9).",
    ),
    ClientRegistration(
        label="VS Code Copilot / IDE",
        transport="HTTP/SSE or STDIO",
        target="the IDE's MCP server registration (stdio block below)",
        note=(
            "stdio shown; the HTTP/SSE variant lands with WP-2.10/2.11. "
            "Check the tool-approval UX when first connecting (Section 10.9)."
        ),
    ),
    ClientRegistration(
        label="OpenCode",
        transport="STDIO",
        target="the client's MCP config (the `mcpServers` entry)",
        note="config key names are verified in WP-2.11.",
    ),
    ClientRegistration(
        label="Aider",
        transport="STDIO or wrapper",
        target="a stdio wrapper invocation (no native MCP config key is asserted)",
        note=(
            "Aider may need a documented instruction snippet instead "
            "(Section 10.9); the command below is what a wrapper must launch."
        ),
        style="command",
    ),
    ClientRegistration(
        label="DeepSeek-based harness",
        transport="Varies",
        target="the harness's MCP registration (stdio shown)",
        note=(
            "text-only client: attachments arrive as OCR transcript plus "
            "layout description (Section 10.9; the rules block covers this)."
        ),
    ),
    ClientRegistration(
        label="Custom agent",
        transport="Either",
        target="your client's MCP registration (stdio shown)",
        note="must pass the Section 10.9 conformance script before production use.",
    ),
)


def _matrix_labels() -> frozenset[str]:
    return frozenset(label for label, _key, _text_only in CLIENT_MATRIX)


def _check_matrix_coverage() -> None:
    """One client list per plan (Section 19.6): registrations mirror the matrix."""
    labels = {registration.label for registration in _CLIENT_REGISTRATIONS}
    if labels != set(_matrix_labels()):  # pragma: no cover - guarded by a test
        raise AssertionError(
            f"client registration labels drifted from CLIENT_MATRIX: "
            f"{sorted(labels)} vs {sorted(_matrix_labels())}"
        )


def bridge_command() -> list[str]:
    """The stdio launch command for *this* machine (Section 10.2).

    Prefers the installed console script when it resolves on ``PATH``
    (portable across installs); otherwise the module form through the
    running interpreter — always valid, and what the snippets show as the
    documented fallback invocation.
    """
    executable = shutil.which(_STDIO_SCRIPT)
    if executable:
        return [executable]
    return [sys.executable, "-m", "orchestrator_bridge", "--mode", "stdio"]


def _command_line(command: Sequence[str]) -> str:
    return " ".join(command)


def _json_block(command: Sequence[str]) -> str:
    args = ", ".join(json.dumps(argument) for argument in command[1:])
    command_field = json.dumps(command[0])
    args_field = f',\n      "args": [{args}]' if command[1:] else ""
    return (
        "{\n"
        '  "mcpServers": {\n'
        '    "orchestrator": {\n'
        f'      "command": {command_field}{args_field}\n'
        "    }\n"
        "  }\n"
        "}"
    )


def render_snippets(*, config_path: Path, command: Sequence[str] | None = None) -> str:
    """The full terminal output: one secret-free registration block per client.

    *config_path* is the user-level config that holds the token — named as
    the source clients must rely on. *command* defaults to
    :func:`bridge_command` (tests inject).
    """
    _check_matrix_coverage()
    cmd = list(command) if command is not None else bridge_command()
    lines = [
        "MCP client registration — the orchestrator bridge (stdio; Section 10.9).",
        "Generated for this machine: terminal output only, never commit these paths.",
        "One server, per-client registration (FR-MCP-01); config syntax is verified",
        "in WP-2.11 — treat field names as the documented shape until then.",
        "",
    ]
    for registration in _CLIENT_REGISTRATIONS:
        lines.append(f"### {registration.label} — transport: {registration.transport}")
        lines.append(f"# target: {registration.target}")
        if registration.note:
            lines.append(f"# note: {registration.note}")
        if registration.style == "json":
            lines.append(_json_block(cmd))
        else:
            lines.append(_command_line(cmd))
        lines.append(
            f"# token: the bridge reads it from {config_path} or "
            "ORCHESTRATOR_AGENT_TOKEN — never from this snippet (FR-SEC-04)."
        )
        lines.append(f"# verify: {_SELF_TEST_POINTER}, or start the bridge under MCP inspector:")
        lines.append(f"#   npx @modelcontextprotocol/inspector {_command_line(cmd)}")
        lines.append("")
    return "\n".join(lines)
