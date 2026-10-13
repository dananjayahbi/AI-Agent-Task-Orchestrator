"""MT-2.7-02 — project-specific rules merging from ``system_prompt_rules``.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.7-rules-injection/
MT-2.7-02-project-rules-merge.md (Sections 10.3 step 5, 10.6, 19, 20.4, 20.5;
FR-MCP-05; gap G-08). Ordering, empty-field behavior, verbatim preservation
apart from documented normalization, and the single-render-path consistency
guarantee across the three delivery channels.
"""

from __future__ import annotations

import pytest

from orchestrator_bridge.rules import (
    PROJECT_RULES_MAX_CHARS,
    normalize_project_rules,
    render_rules,
    render_session_rules,
)

_PROJECT_RULE = "Keep the ERP invoices deterministic."


def test_project_rules_appear_after_the_standard_rules() -> None:
    text = render_rules("coder", project_rules=_PROJECT_RULE)
    standard_at = text.index("8. Provide a clear execution summary.")
    project_at = text.index(_PROJECT_RULE)
    assert standard_at < project_at  # Section 10.6 ordering: appended last
    assert text.index("Project rules:") < project_at


def test_auditor_render_also_appends_project_rules() -> None:
    text = render_rules("auditor", project_rules=_PROJECT_RULE)
    assert text.index("4. Report honest confidence") < text.index(_PROJECT_RULE)


@pytest.mark.parametrize("empty", ["", "   ", "\n\t"])
def test_missing_or_empty_project_rules_render_no_section_artifact(empty: str) -> None:
    text = render_rules("coder", project_rules=empty)
    assert "Project rules:" not in text
    assert text.endswith("8. Provide a clear execution summary.")


def test_owner_wording_is_preserved_verbatim() -> None:
    owner = "Never merge on Fridays.\nAlways ping @release-first."
    text = render_rules("coder", project_rules=owner)
    assert owner in text  # newline and wording untouched


def test_normalization_strips_control_characters_only() -> None:
    dirty = "Rule\x00one.\x1b[31m Rule\x07 two.\nKeep\tthis."
    cleaned = normalize_project_rules(dirty)
    assert "\x00" not in cleaned
    assert "\x1b" not in cleaned
    assert "\x07" not in cleaned
    # Only the control characters go; printable residue stays (minimal handling).
    assert "Ruleone.[31m Rule two.\nKeep\tthis." == cleaned


def test_overlong_project_rules_are_capped_with_a_visible_marker() -> None:
    huge = "x" * (PROJECT_RULES_MAX_CHARS + 500)
    cleaned = normalize_project_rules(huge)
    assert cleaned.endswith("[project rules truncated: limit reached]")
    assert len(cleaned) < len(huge)


def test_project_rules_are_never_rendered_twice() -> None:
    text = render_rules("coder", project_rules=_PROJECT_RULE)
    assert text.count(_PROJECT_RULE) == 1
    assert text.count("Project rules:") == 1


def test_single_render_path_is_consistent_across_channels() -> None:
    """The three G-08 channels produce identical text for the same inputs.

    ``get_project_context`` and the initialize instructions both call
    ``render_session_rules``; the claim path calls ``render_rules`` with the
    same project rules — all three must agree byte-for-byte for the same
    role/session inputs (MT-2.7-02/03 acceptance).
    """
    policy = {"lease_duration_minutes": 45}
    session_text = render_session_rules("coder", project_rules=_PROJECT_RULE, policy_summary=policy)
    claim_text = render_rules(
        "coder",
        checkpoint_minutes=45 // 3,
        project_rules=_PROJECT_RULE,
    )
    assert session_text == claim_text


def test_session_render_uses_policy_lease_for_the_checkpoint_interval() -> None:
    text = render_session_rules(
        "coder", project_rules="", policy_summary={"lease_duration_minutes": 60}
    )
    assert "every 20 minutes" in text  # 60 // 3


def test_session_render_falls_back_to_the_section_7_2_default_lease() -> None:
    for summary in ({}, {"lease_duration_minutes": "not-a-number"}, {"lease_duration_minutes": 0}):
        text = render_session_rules("coder", project_rules="", policy_summary=summary)
        assert f"every {45 // 3} minutes" in text


def test_normalization_never_interpolates_or_executes_owner_text() -> None:
    """Owner text is data: braces and template syntax survive literally."""
    owner = "Use {placeholder} syntax; do not .format() anything."
    text = render_rules("coder", project_rules=owner)
    assert "{placeholder}" in text
