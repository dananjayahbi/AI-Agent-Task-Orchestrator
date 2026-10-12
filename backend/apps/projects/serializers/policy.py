"""Request/response contract for ``/projects/{pid}/policy`` (MT-1.3-04).

One serializer serves **both** directions (Section 9.2):

* ``GET`` renders every Section 7.2 field with its current values — the
  same shape FR-PRJ-05 enumerates;
* ``PATCH`` validates only what the plan states (MT-1.3-04 risk note —
  *nothing* beyond it is invented as hard policy): enums are the closed
  Section 7.2 vocabularies, durations/retries/thresholds are positive,
  ``auditor_min_confidence`` is 1–5, ``max_concurrent_tasks`` may be 0
  (G-26's semantics — 0 pauses claiming without changing
  ``active_status``), and branch prefix / glob lists must be non-empty
  *when supplied*. Glob **semantics** (matching against real files) are the
  Policy Engine's concern, WP-3.x — not this endpoint.

Partial-update semantics are explicit: patching one field leaves every
other field at its current value (the strict mixin additionally rejects
unknown keys rather than ignoring them — MT-1.3-04 AC).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from ..models import LeaseExtensionMode, MergeStrategy, ProjectPolicy
from .base import StrictSerializerMixin


class ProjectPolicySerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """The Section 7.2 policy table as a validated read/write contract."""

    lease_duration_minutes = serializers.IntegerField(
        min_value=1,
        help_text="Lease length and per-checkpoint extension; default 45 (7.2).",
    )
    lease_max_total_minutes = serializers.IntegerField(
        min_value=1,
        help_text="Hard cap on one continuous claim; default 240 (7.2).",
    )
    lease_extension_mode = serializers.ChoiceField(
        choices=LeaseExtensionMode.choices,
        help_text=(
            "checkpoint_only (default) or checkpoint_and_liveness (per-project "
            "option — OQ-04's recommended product default is unchanged)."
        ),
    )
    max_retries = serializers.IntegerField(
        min_value=1,
        help_text="Lease failures before escalation; default 3 (7.2).",
    )
    max_concurrent_tasks = serializers.IntegerField(
        min_value=0,
        help_text=(
            "Simultaneous in_progress tasks; default 1 (G-26). 0 is legal: it "
            "pauses claiming without touching active_status."
        ),
    )
    autonomous_diff_threshold_lines = serializers.IntegerField(
        min_value=1,
        help_text="Max changed lines for auto-complete; default 250 (7.2).",
    )
    auditor_min_confidence = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text="Minimum auditor confidence, 1-5; default 4 (7.2).",
    )
    critical_path_globs = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=False,
        help_text="Escalating paths (CI/CD, root migrations, security config).",
    )
    migration_path_globs = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=False,
        help_text="Escalating framework-specific migration paths.",
    )
    sensitive_config_globs = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=False,
        help_text="Escalating env/key/security-rule paths.",
    )
    auto_complete_enabled = serializers.BooleanField(
        help_text="If false, every task goes to human review; default true (7.2).",
    )
    merge_strategy = serializers.ChoiceField(
        choices=MergeStrategy.choices,
        help_text="squash (default) / merge_commit / fast_forward_only (7.2).",
    )
    branch_prefix = serializers.CharField(
        allow_blank=False,
        help_text=(
            "Canonical branch-name prefix, `{PID}` resolved per project when "
            "names are derived (G-09; default `feat/{PID}-`). Changing it "
            "affects bridge branch naming from WP-2.x on."
        ),
    )
    audit_required_default = serializers.BooleanField(
        help_text="Default audit_required for new tasks; default true (7.2).",
    )
    stalled_after_minutes = serializers.IntegerField(
        min_value=1,
        help_text="UI warning when no checkpoint arrives; default 20 (7.2).",
    )

    def update(self, instance: ProjectPolicy, validated_data: dict[str, Any]) -> ProjectPolicy:
        """Apply the partial update; every Section 7.2 field stays in sync.

        ``instance`` is the project's ``agent_policy`` row (never a new
        policy — policies are created as pairs by ``create_project`` and
        edited only here, Section 12.5's "the only supported way").
        """
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        return instance


__all__ = ["ProjectPolicySerializer"]
