"""MT-2.1-01 — package layout: seams import, empty registry, independent-deployable boundary.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.1-bridge-skeleton/MT-2.1-01-package-layout.md
(parent plan Appendix A, Section 10.1, Section 19.1; independent-deployable boundary).
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import orchestrator_bridge
from orchestrator_bridge.tools import TOOLS
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES

PACKAGE_ROOT = Path(orchestrator_bridge.__file__).resolve().parent
TESTS_ROOT = Path(__file__).resolve().parent

# The Section 10.1 responsibility seams MT-2.1-01 seeds (config/logging are filled
# by MT-2.1-02/03; the rest stay placeholders until their WPs).
SEAMS = (
    "orchestrator_bridge.config",
    "orchestrator_bridge.logging",
    "orchestrator_bridge.manifest",
    "orchestrator_bridge.capabilities",
    "orchestrator_bridge.credentials",
    "orchestrator_bridge.resume_cache",
    "orchestrator_bridge.tools",
)

# The monorepo packages the bridge must never import (independent deployables).
_FORBIDDEN_IMPORT = re.compile(r"^\s*(?:from|import)\s+(?:backend|web)\b", re.MULTILINE)


def test_all_seams_import() -> None:
    """Every placeholder module is importable and docstringed (smoke import)."""
    for name in SEAMS:
        module = importlib.import_module(name)
        assert module.__doc__, f"{name} must carry a plan-section docstring"


def test_tools_registry_lists_the_catalog_tools() -> None:
    """WP-2.4/MT-2.4-01, extended by WP-2.6/2.5/3.5: the registry is exactly
    Section 10.5's catalog as landed so far — the five core tools plus the
    checkpoint/submission pair, the attachment reader (WP-2.5) and the
    auditor verdict tool (WP-3.5).

    (The WP-2.1 "empty tool set" contract survives as ``create_server``
    without a bound runtime — asserted in ``test_entrypoints.py``.)
    """
    assert tuple(TOOLS) == CORE_TOOL_NAMES
    assert set(TOOLS) == {
        "get_available_tasks",
        "get_task_details",
        "claim_task",
        "read_task_attachment",
        "log_task_checkpoint",
        "submit_task_resolution",
        "release_task",
        "submit_audit_verdict",
        "create_draft_task",
        "get_project_context",
    }


def test_no_backend_or_web_imports() -> None:
    """ADR/Appendix A boundary: bridge code never imports backend/ or web/."""
    offenders = []
    for root in (PACKAGE_ROOT, TESTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            if _FORBIDDEN_IMPORT.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(PACKAGE_ROOT.parent)))
    assert offenders == [], f"cross-package imports found: {offenders}"
