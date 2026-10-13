"""OpenAPI contract for ``GET /dashboard/summary`` (MT-1.15-06; FR-MOB-01).

The wire shape is the one the WP-5.6 gap note recommended and the
hand-authored mobile ``DashboardSummary`` model reconciles against: a
top-level ``projects`` array of cards carrying per-state counts (the six
canonical G-01 keys, zero-filled), velocity and active agents
(Section 14.1 Home / Overview). Not a pagination.md list — the dashboard
summary is a single-resource GET (pagination.md names it explicitly).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class StateCountsSerializer(serializers.Serializer[Any]):
    """The six canonical G-01/ADR-010 state counts, always all present.

    Zero-filled by the service: a state with no tasks reads ``0``, never
    an absent key — the mobile card renders every column from these keys
    and never invents its own (G-01; MT-5.6-01).
    """

    draft = serializers.IntegerField(
        min_value=0,
        help_text="Tasks in draft (Section 8.2 T1).",
    )
    pending = serializers.IntegerField(
        min_value=0,
        help_text="Tasks visible to agents for claiming (Section 8.2).",
    )
    in_progress = serializers.IntegerField(
        min_value=0,
        help_text="Tasks under an active coder lease (Section 8.6).",
    )
    to_be_audited = serializers.IntegerField(
        min_value=0,
        help_text="Submissions awaiting an auditor claim (Section 8.2).",
    )
    in_human_review = serializers.IntegerField(
        min_value=0,
        help_text=(
            "Tasks escalated to the Owner — the mobile 'needs review' "
            "banner derives from this count (Section 14.1; FR-MOB-04)."
        ),
    )
    completed = serializers.IntegerField(
        min_value=0,
        help_text="Completed tasks; immutable except archive (Section 7.4 rule 3).",
    )


class ProjectDashboardCardSerializer(serializers.Serializer[Any]):
    """One project's Overview card — Section 14.1 Home row; FR-MOB-01."""

    project_id = serializers.CharField(
        help_text="Canonical PID + five digits (Section 7.3), in id order.",
    )
    name = serializers.CharField()
    state_counts = StateCountsSerializer(
        help_text=(
            "Counts over the project's non-archived tasks, keyed by the six "
            "canonical G-01 states, zero-filled (ADR-010; T19 visibility)."
        ),
    )
    velocity = serializers.IntegerField(
        min_value=0,
        help_text=(
            "Tasks that reached `completed` in the trailing 7-day window "
            "(server clock, transition log). Conservative documented "
            "default — the plan states no definition (OQ); this payload is "
            "authoritative and clients never recompute it (FR-MOB-01)."
        ),
    )
    active_agents = serializers.IntegerField(
        min_value=0,
        help_text=(
            "AgentSession rows of this project with ended_at null "
            "(Section 7.2 lifecycle; no heartbeat freshness invented)."
        ),
    )


class DashboardSummarySerializer(serializers.Serializer[Any]):
    """``GET /dashboard/summary`` body — one card per registered project."""

    projects = ProjectDashboardCardSerializer(
        many=True,
        help_text=(
            "Every registered project, ordered by project id; empty when no "
            "projects exist. Single-resource GET — no cursor pagination "
            "(pagination.md)."
        ),
    )


__all__ = [
    "DashboardSummarySerializer",
    "ProjectDashboardCardSerializer",
    "StateCountsSerializer",
]
