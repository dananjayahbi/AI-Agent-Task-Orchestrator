"""MT-2.7-04 — per-client fallback instruction snippets (gap G-08).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.7-rules-injection/
MT-2.7-04-client-fallback-snippets.md (Sections 10.6, 10.9, 19, 20.4, 20.5;
FR-MCP-05, NFR-08). One snippet per Section 10.9 matrix client row, generated
from the MT-2.7-01 render source and pinned to it — the committed guide file
``docs/agent-guides/rules-fallback-snippets.md`` may not drift from
``render_client_snippet`` (Section 20.5: no hand-retyped copy).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from orchestrator_bridge.rules import (
    CLIENT_MATRIX,
    CODER_RULES,
    render_client_snippet,
)

BRIDGE_ROOT = Path(__file__).resolve().parent.parent
GUIDE = BRIDGE_ROOT.parent / "docs" / "agent-guides" / "rules-fallback-snippets.md"

#: The six Section 10.9 matrix rows, by snippet key (MT acceptance criterion 1).
_MATRIX_KEYS = (
    "claude-code",
    "vscode-copilot",
    "opencode",
    "aider",
    "deepseek-harness",
    "custom-agent",
)


def _guide_text() -> str:
    assert GUIDE.is_file(), f"guide file missing: {GUIDE} — run scripts/generate_rules_snippets.py"
    return GUIDE.read_text(encoding="utf-8")


def test_one_snippet_exists_for_each_section_10_9_matrix_row() -> None:
    assert tuple(key for _label, key, _text_only in CLIENT_MATRIX) == _MATRIX_KEYS
    guide = _guide_text()
    for _label, key, _text_only in CLIENT_MATRIX:
        snippet = render_client_snippet(key)
        assert snippet in guide, f"snippet for {key} missing or drifted from render source"


def test_every_snippet_carries_all_eight_section_10_6_rules() -> None:
    for _label, key, _text_only in CLIENT_MATRIX:
        snippet = render_client_snippet(key)
        for rule in CODER_RULES:
            # Rule text modulo slot substitution (generic phrasings render).
            head = rule.split(" (")[0]  # e.g. "1. Work only on the assigned branch"
            head = re.sub(r" \{checkpoint_minutes\} minutes", "", head)
            assert head in snippet, f"{key} snippet lost rule: {head}"


def test_text_only_clients_carry_the_rule_6_variant_note() -> None:
    for _label, key, text_only in CLIENT_MATRIX:
        snippet = render_client_snippet(key)
        if text_only:
            assert "Text-only note" in snippet
        else:
            assert "Text-only note" not in snippet


def test_snippets_state_the_fallback_status_and_nfr_08_sufficiency() -> None:
    guide = _guide_text()
    assert "fallback" in guide.lower()
    assert "NFR-08" in guide
    assert "authoritative" in guide


def test_no_client_config_syntax_is_asserted_as_verified() -> None:
    """WP-2.11 owns verification — the guide must say so, per the MT risk note."""
    guide = _guide_text()
    assert "verified in WP-2.11" in guide
    assert "unverified" in guide or "To verify" in guide or "are verified" in guide


def test_unknown_client_key_is_a_clear_error() -> None:
    import pytest

    with pytest.raises(KeyError, match="unknown client key"):
        render_client_snippet("not-a-client")


def test_guide_generation_is_reproducible_from_the_script() -> None:
    """The committed file equals the generator script's output, byte for byte."""
    sys.path.insert(0, str(BRIDGE_ROOT / "scripts"))
    try:
        from generate_rules_snippets import render_guide
    finally:
        sys.path.pop(0)
    assert _guide_text() == render_guide()
