"""Render a project's ``orchestrator.json`` manifest (Section 10.3; MT-1.3-05).

The manifest is how project context reaches a repository **without the
backend ever touching it** (ADR-007) and it holds no secrets — it is safe
to commit (FR-SEC-04; Section 10.3). This renderer therefore reads only
the allowlisted Section 7.2/10.3 fields; the schema
(``schemas/manifest.v1.json``) carries ``additionalProperties: false`` so
a key outside the contract cannot appear even by accident, and the tests
assert the exact key set (WP-1.3 acceptance: "generated manifest passes
schema validation").

Recorded decisions (MT-1.3-05 risk notes, WP changelog):

* ``$schema`` keeps the **Section 10.3 example's URL verbatim**
  (``https://orchestrator.local/schemas/manifest.v1.json``) — the plan is
  authoritative and WP-2.2 (bridge validation) confirms or replaces it;
  the published file's basename matches that path (`schemas/manifest.v1.json`).
* ``orchestrator_api`` comes from the ``ORCHESTRATOR_API_BASE_URL``
  setting (Section 9.10 group; NFR-06 env-only) — local Compose and tunnel
  deployments (Section 15) differ, so it is never baked into code.
* ``auto_branch_prefix`` is the policy ``branch_prefix`` (G-09, default
  ``feat/{PID}-``) with ``{PID}`` resolved to the concrete project id —
  the Section 10.3 example shows ``feat/PID00007-``, i.e. already resolved;
  a prefix without the token passes through unchanged.
* ``agent_hints`` renders the Section 10.3 example's defaults (all hint
  keys optional).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings

from ..models import Project

# The Section 10.3 example's $schema URL — placeholder host kept verbatim
# (decision recorded in the changelog; WP-2.2 confirms).
MANIFEST_SCHEMA_URL = "https://orchestrator.local/schemas/manifest.v1.json"

# Section 10.3 manifest generation — the only value that ships.
MANIFEST_SCHEMA_VERSION = 1

# The FR-SEC-04 allowlist: exactly these top-level keys may appear.
MANIFEST_KEYS: frozenset[str] = frozenset(
    {
        "$schema",
        "schema_version",
        "project_id",
        "project_name",
        "orchestrator_api",
        "default_branch",
        "auto_branch_prefix",
        "audit_required_default",
        "agent_hints",
    }
)


def resolve_branch_prefix(branch_prefix: str, project_id: str) -> str:
    """Apply the G-09 `{PID}` template token to a policy prefix."""
    return branch_prefix.replace("{PID}", project_id)


def render_manifest(project: Project) -> dict[str, Any]:
    """Build the Section 10.3 manifest document for *project*.

    Pure projection of the Section 7.2 fields plus configuration — no
    request input, no secrets, nothing outside ``MANIFEST_KEYS`` (asserted
    by tests and enforced downstream by the schema's allowlist).
    """
    policy = project.agent_policy
    return {
        "$schema": MANIFEST_SCHEMA_URL,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "project_id": project.id,
        "project_name": project.name,
        "orchestrator_api": settings.ORCHESTRATOR_API_BASE_URL,
        "default_branch": project.default_branch,
        "auto_branch_prefix": resolve_branch_prefix(policy.branch_prefix, project.id),
        "audit_required_default": policy.audit_required_default,
        # Section 10.3 example defaults; all agent_hints keys optional.
        "agent_hints": {
            "test_command_default": "see task",
            "worktree_mode": False,
        },
    }
