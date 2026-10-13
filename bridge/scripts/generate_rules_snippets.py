"""Regenerate ``docs/agent-guides/rules-fallback-snippets.md`` (MT-2.7-04).

The committed guide's snippet bodies are rendered from
:mod:`orchestrator_bridge.rules` — the single Section 10.6 source — so a
template edit propagates by re-running this script instead of hand-editing
prose. ``tests/test_rules_snippets.py`` pins the committed file to this
generation; run it after any rules-template change:

    uv run --directory bridge python scripts/generate_rules_snippets.py
"""

from __future__ import annotations

from pathlib import Path

from orchestrator_bridge.rules import CLIENT_MATRIX, render_client_snippet

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TARGET = REPO_ROOT / "docs" / "agent-guides" / "rules-fallback-snippets.md"

_HEADER = """\
# Rules fallback instruction snippets (gap G-08)

> **Status: fallback reinforcement.** The MCP tools and the `claim_task`
> response's mandatory `rules` block are the authoritative delivery channels
> and remain sufficient on their own (NFR-08 — the tool-only contract). Some
> clients do not surface MCP server `instructions` (parent plan Section 10.9
> matrix, several rows still "To verify"); for those, paste the matching
> snippet below into the client's system-prompt / instructions configuration
> so the Section 10.6 rules are enforced even when the client ignores the
> initialize response.
>
> **Generated file:** every snippet is rendered from
> `bridge/src/orchestrator_bridge/rules.py` (`render_client_snippet`) and
> pinned by `bridge/tests/test_rules_snippets.py` — do not hand-edit the
> snippet bodies; edit the render source and re-run this script. Which
> clients actually need these snippets, and their exact config syntax, are
> verified and published in WP-2.11 — no config syntax is asserted as
> verified here.
>
> One snippet per Section 10.9 matrix row: Claude Code CLI, VS Code Copilot /
> IDE, OpenCode, Aider, DeepSeek-based harness, Custom agent.
"""


def render_guide() -> str:
    """The full guide document — header plus one generated snippet per client."""
    parts = [_HEADER]
    for _label, key, _text_only in CLIENT_MATRIX:
        parts.append(render_client_snippet(key))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(render_guide(), encoding="utf-8")
    print(f"wrote {TARGET} ({TARGET.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
