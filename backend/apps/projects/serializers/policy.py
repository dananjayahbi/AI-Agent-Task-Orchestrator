"""Request/response contract for ``/projects/{pid}/policy`` (MT-1.3-04).

One serializer serves **both** directions (Section 9.2):

* ``GET`` renders every Section 7.2 field with its current values — the
  same shape FR-PRJ-05 enumerates;
* ``PATCH`` validates what the plan states plus the WP-3.1 additions:
  enums are the closed Section 7.2 vocabularies, durations/retries/
  thresholds are positive, ``auditor_min_confidence`` is 1–5,
  ``max_concurrent_tasks`` may be 0 (G-26's semantics — 0 pauses
  claiming without changing ``active_status``), branch prefix / glob
  lists must be non-empty *when supplied*, and — since MT-3.1-03 — the
  three glob fields obey the Section 12.3 rules (syntax, repo-root
  relative, no ``..`` traversal) through the shared validator in
  ``apps.projects.services.globs``, while
  ``lease_max_total_minutes >= lease_duration_minutes`` holds across a
  patch. Glob *semantics* (matching against real files) remain the
  Policy Engine's concern (WP-3.4) — not this endpoint.

MT-3.1-02 adds the write-only ``policy_preset`` input: apply a
framework preset (fills the three glob fields in one action). It is an
input affordance, never stored and never rendered — the GET shape stays
exactly the Section 7.2 field set, and combining it with explicit glob
fields in one request is refused (the conflict rule) rather than
silently ordering the operations.

Partial-update semantics are explicit: patching one field leaves every
other field at its current value (the strict mixin additionally rejects
unknown keys rather than ignoring them — MT-1.3-04 AC).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import LeaseExtensionMode, MergeStrategy, ProjectPolicy
from ..policy_presets import PRESET_IDS, get_preset, list_presets, preset_glob_fields
from ..services.globs import validate_glob_list
from .base import StrictSerializerMixin

_GLOB_FIELDS = ("critical_path_globs", "migration_path_globs", "sensitive_config_globs")


class ProjectPolicySerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """The Section 7.2 policy table as a validated read/write contract."""

    lease_duration_minutes = serializers.IntegerField(
        min_value=1,
        help_text="Lease length and per-checkpoint extension; default 45 (7.2).",
    )
    lease_max_total_minutes = serializers.IntegerField(
        min_value=1,
        help_text=(
            "Hard cap on one continuous claim; default 240 (7.2). Must be "
            ">= lease_duration_minutes (MT-3.1-03 cross-field rule)."
        ),
    )
    lease_extension_mode = serializers.ChoiceField(
        choices=LeaseExtensionMode.choices,
        help_text=(
            "checkpoint_only (default) or checkpoint_and_liveness (per-project "
            "option — OQ-04's recommended product default is unchanged; "
            "checkpoint_only is the enforced default, MT-3.1-01)."
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
        help_text=(
            "Escalating paths (CI/CD, root migrations, security config). "
            "Section 12.3 rules apply (MT-3.1-03): syntax-checked, "
            "repo-root-relative, no '..' traversal."
        ),
    )
    migration_path_globs = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=False,
        help_text=(
            "Escalating framework-specific migration paths; Section 12.3 rules apply (MT-3.1-03)."
        ),
    )
    sensitive_config_globs = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=False,
        help_text=("Escalating env/key/security-rule paths; Section 12.3 rules apply (MT-3.1-03)."),
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
    # Write-only input affordance (MT-3.1-02): expands into the three glob
    # fields inside validate(); never stored, never rendered on GET, so the
    # response shape stays exactly the Section 7.2 field set.
    policy_preset = serializers.ChoiceField(
        choices=PRESET_IDS,
        required=False,
        write_only=True,
        help_text=(
            "Apply a framework preset (WP-3.1): fills critical_path_globs, "
            "migration_path_globs and sensitive_config_globs in one action. "
            "Unknown ids are rejected; combining it with any explicit glob "
            "field in the same request is refused (no implicit ordering). "
            "Omitting it leaves the patched globs as sent."
        ),
    )

    def validate_critical_path_globs(self, value: list[str]) -> list[str]:
        """Section 12.3 discipline via the shared matcher module (MT-3.1-03).

        ``field=None``: DRF keys the raised per-index detail under this
        field's name itself (single wrap — see ``validate_glob_list``).
        """
        return validate_glob_list(value)

    def validate_migration_path_globs(self, value: list[str]) -> list[str]:
        """Section 12.3 discipline via the shared matcher module (MT-3.1-03)."""
        return validate_glob_list(value)

    def validate_sensitive_config_globs(self, value: list[str]) -> list[str]:
        """Section 12.3 discipline via the shared matcher module (MT-3.1-03)."""
        return validate_glob_list(value)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Preset expansion (MT-3.1-02) + the lease-cap cross-field rule (MT-3.1-03).

        Both run on the *merged* partial view: a field absent from this
        patch takes its current value off ``instance`` before the lease
        comparison, so a valid row can never be put into an invalid
        combination by patching one side alone. The instance is skipped
        only when the serializer runs without one (the shared-schema
        callers) — then both sides must come from the payload itself.
        """
        attrs = super().validate(attrs)

        # MT-3.1-02: preset → three glob fields, or an explicit conflict.
        preset_id = attrs.get("policy_preset")
        if preset_id is not None:
            conflicts = [name for name in _GLOB_FIELDS if name in attrs]
            if conflicts:
                raise ValidationError(
                    {
                        "policy_preset": [
                            "Cannot be combined with explicit glob fields "
                            f"({', '.join(conflicts)}) in one request; apply "
                            "the preset alone or patch the globs directly."
                        ]
                    }
                )
            # ChoiceField already resolved the id; get_preset re-checks so
            # direct service callers share the catalog answer, and
            # preset_glob_fields runs the Section 12.3 validator on the
            # preset data (runtime guard for MT-3.1-02's AC).
            attrs.update(preset_glob_fields(get_preset(preset_id)))
        attrs.pop("policy_preset", None)  # input-only; never reaches update()/events

        # MT-3.1-03: the cap must cover the base duration on the merged row.
        instance = self.instance if isinstance(self.instance, ProjectPolicy) else None
        duration = attrs.get(
            "lease_duration_minutes",
            instance.lease_duration_minutes if instance is not None else None,
        )
        total = attrs.get(
            "lease_max_total_minutes",
            instance.lease_max_total_minutes if instance is not None else None,
        )
        if duration is not None and total is not None and total < duration:
            raise ValidationError(
                {"lease_max_total_minutes": [f"Must be >= lease_duration_minutes ({duration})."]}
            )
        return attrs

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


class PolicyPresetSerializer(serializers.Serializer[Any]):
    """Read-only DTO of one preset — WP-3.1's listing surface (MT-3.1-02).

    The library is served as a DTO (not a new Section 9.2 route): the
    ``policy_preset`` ChoiceField on both input serializers publishes the
    selectable ids in the generated OpenAPI, and this DTO renders one
    preset's full glob payload for API clients and the WP-4.10 surfaces
    that will eventually display the choices. Instance-driven, so it
    serializes ``PolicyPreset`` dataclasses from ``list_presets()``.
    """

    id = serializers.CharField(help_text="Stable selection id; sent as `policy_preset`.")
    title = serializers.CharField()
    description = serializers.CharField()
    critical_path_globs = serializers.ListField(child=serializers.CharField())
    migration_path_globs = serializers.ListField(child=serializers.CharField())
    sensitive_config_globs = serializers.ListField(child=serializers.CharField())


def render_presets() -> list[dict[str, Any]]:
    """The whole library as DTO dicts (test- and client-facing listing)."""
    return [PolicyPresetSerializer(preset).data for preset in list_presets()]


__all__ = ["PolicyPresetSerializer", "ProjectPolicySerializer", "render_presets"]
