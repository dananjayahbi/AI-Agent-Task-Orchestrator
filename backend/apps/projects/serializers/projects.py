"""Request/response contracts for the Projects row (Section 9.2; MT-1.3-03).

Shapes mirror the OpenAPI operations:

* ``ProjectSerializer`` — the read model: every Section 7.2 field, with the
  server-managed ones (``id``, ``agent_policy``, ``task_counter``,
  timestamps) read-only. ``agent_policy`` renders as the policy row's
  integer id — the policy *contents* belong to ``GET /projects/{pid}/policy``
  (MT-1.3-04), never here.
* ``ProjectCreateSerializer`` — ``POST /projects``: the Section 9.2
  create inputs plus the optional WP-3.1 ``policy_preset`` selection
  (MT-3.1-02 — a preset *adds* a selection knob, it introduces no new
  Section 7.2 policy field); the id is never among them (FR-PRJ-01 —
  server-assigned), and the strict mixin turns a client-supplied ``id``
  into ``VALIDATION_ERROR`` rather than silently dropping it.
* ``ProjectUpdateSerializer`` — ``PATCH /projects/{pid}``: the FR-PRJ-02
  mutable fields incl. ``active_status`` transitions; partial semantics
  (MT-1.3-04's AC wording applies here too: patching one field leaves the
  others untouched). ``id`` is *not* declared — an attempted id change is
  rejected as unknown (immutability, Section 7.3/7.4).
* list envelope/query — pagination.md's two-member cursor contract, as
  published by WP-0.5.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.pagination import MAX_PAGE_SIZE

from ..models import ActiveStatus, Project
from ..policy_presets import PRESET_IDS
from .base import StrictSerializerMixin


class ProjectSerializer(serializers.Serializer[Any]):
    """GET representations of a project — Section 7.2 fields, in plan order."""

    id = serializers.CharField(
        read_only=True,
        help_text="Server-assigned PID + five digits (Section 7.3); immutable.",
    )
    name = serializers.CharField(max_length=200)
    repo_path = serializers.CharField(
        max_length=500,
        help_text="Path as seen by the bridge host (informational for the backend).",
    )
    active_status = serializers.ChoiceField(
        choices=ActiveStatus.choices,
        help_text="active | paused | archived (FR-PRJ-04).",
    )
    default_branch = serializers.CharField(max_length=255)
    system_prompt_rules = serializers.CharField(
        allow_blank=True,
        help_text="Markdown text fed into the rules block (Section 10.6).",
    )
    agent_policy = serializers.IntegerField(
        source="agent_policy.pk",
        read_only=True,
        help_text="The project's one-to-one Project Policy row (Section 7.1).",
    )
    task_counter = serializers.IntegerField(
        read_only=True,
        help_text="Atomic task index source for MT-1.4-02 (starts at 0).",
    )
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ProjectCreateSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """POST /projects body — Section 9.2 create inputs + WP-3.1 preset."""

    name = serializers.CharField(max_length=200)
    repo_path = serializers.CharField(max_length=500)
    default_branch = serializers.CharField(max_length=255)
    system_prompt_rules = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional at creation; editable afterwards via PATCH.",
    )
    policy_preset = serializers.ChoiceField(
        choices=PRESET_IDS,
        required=False,
        help_text=(
            "Optional framework preset (WP-3.1, MT-3.1-02): seeds the new "
            "project's policy with the preset's critical/migration/sensitive "
            "globs. Omitted = the Section 7.2 stock defaults. Unknown ids "
            "are VALIDATION_ERROR."
        ),
    )


class ProjectUpdateSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """PATCH /projects/{pid} body — every FR-PRJ-02 mutable field, optional."""

    name = serializers.CharField(max_length=200, required=False)
    repo_path = serializers.CharField(max_length=500, required=False)
    default_branch = serializers.CharField(max_length=255, required=False)
    system_prompt_rules = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    active_status = serializers.ChoiceField(
        choices=ActiveStatus.choices,
        required=False,
        help_text="Transitions among active | paused | archived (FR-PRJ-04).",
    )

    def update(self, instance: Project, validated_data: dict[str, Any]) -> Project:
        """Apply the partial update; server-managed fields are undeclared.

        Mirrors ModelSerializer semantics on a hand-written serializer:
        only declared keys reach the instance, ``id`` is rejected upstream
        by the strict mixin, and ``save()`` bumps ``updated_at`` while the
        model's immutability guard keeps refusing id changes (7.3/7.4).
        """
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        return instance


class ProjectListEnvelopeSerializer(serializers.Serializer[Any]):
    """pagination.md envelope: exactly ``results`` + ``next_cursor``."""

    results = ProjectSerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque cursor for the next page; null = end of list.",
    )


class ProjectListQuerySerializer(serializers.Serializer[Any]):
    """GET /projects query parameters (cursor contract)."""

    cursor = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Opaque cursor from the previous page's next_cursor.",
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text=(
            f"Items per page (default 25, maximum {MAX_PAGE_SIZE}; values "
            "above the maximum are clamped — pagination.md documented "
            "defaults, same per-endpoint choice as GET /tokens)."
        ),
    )


__all__ = [
    "ProjectCreateSerializer",
    "ProjectListEnvelopeSerializer",
    "ProjectListQuerySerializer",
    "ProjectSerializer",
    "ProjectUpdateSerializer",
]
