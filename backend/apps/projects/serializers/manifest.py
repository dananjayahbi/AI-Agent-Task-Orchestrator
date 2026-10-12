"""OpenAPI contract for ``GET /projects/{pid}/manifest`` (MT-1.3-05).

The response *is* the Section 10.3 document — nine allowlisted keys,
rendered by ``services.manifest``. DRF field names must be Python
identifiers, and the contract's first key is ``$schema``; the class below
is therefore assembled via ``type()`` with a dict of declared fields (a
class body cannot spell ``$schema = ...``). The serializer documents the
wire shape for ADR-005's generated contract — the view returns the raw
rendered dict so nothing can drift between two representations.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class AgentHintsSerializer(serializers.Serializer[Any]):
    """Section 10.3 ``agent_hints`` — every key optional."""

    test_command_default = serializers.CharField(
        required=False,
        help_text='Fallback test-command hint (Section 10.3 example: "see task").',
    )
    worktree_mode = serializers.BooleanField(
        required=False,
        help_text="Per-task worktree advice (Section 10.3 example: false; ADR-013).",
    )


# ``type()`` assembles the class because `$schema` is not a legal class
# attribute name (see module docstring); annotated so mypy and drf-
# spectacular see a serializer class, not bare ``type``.
OrchestratorManifest: type[serializers.Serializer[Any]] = type(
    "OrchestratorManifest",
    (serializers.Serializer,),
    {
        "__module__": __name__,
        "$schema": serializers.CharField(
            help_text="Location of the manifest schema (Section 10.3).",
        ),
        "schema_version": serializers.IntegerField(
            help_text="Manifest generation — always 1 (Section 10.3).",
        ),
        "project_id": serializers.CharField(
            help_text="Canonical PID + five digits (Section 7.3).",
        ),
        "project_name": serializers.CharField(),
        "orchestrator_api": serializers.CharField(
            help_text=(
                "API base URL from ORCHESTRATOR_API_BASE_URL (Section 9.10 / "
                "NFR-06 — configuration, never code)."
            ),
        ),
        "default_branch": serializers.CharField(),
        "auto_branch_prefix": serializers.CharField(
            help_text="Policy branch_prefix with {PID} resolved (G-09).",
        ),
        "audit_required_default": serializers.BooleanField(
            help_text="Policy default for new tasks (Section 7.2).",
        ),
        "agent_hints": AgentHintsSerializer(
            required=False,
            help_text="All hint keys optional (Section 10.3).",
        ),
    },
)

__all__ = ["AgentHintsSerializer", "OrchestratorManifest"]
