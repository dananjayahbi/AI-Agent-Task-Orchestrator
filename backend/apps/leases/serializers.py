"""Claim / release / work serializers (Section 9.2 Agent-work rows; MT-1.6-07).

* ``ClaimRequest`` — the Section 10.5 ``claim_task`` tool inputs that
  map onto the API: the session id (G-18; the bridge's
  ``agent_session_id``), the human-readable worker label
  (``agent_identifier`` — G-18: a label only) and, since WP-3.3
  (MT-3.3-01), the Section 10.5 ``role`` input (coder default,
  auditor). The role is *request intent*, never trust: the token's
  scopes answer first (Section 12.2) and the claim service validates
  the declared role against the row's state inside the lock (mismatch →
  ``ROLE_NOT_PERMITTED``).
* ``ReleaseRequest`` — the fencing pair (``session_id`` +
  ``lease_generation``, ADR-012's carrier on agent mutations), an
  optional free-text ``reason`` (Section 10.5 ``release_task`` input →
  the Transition row's note), and an optional ``version`` for the
  optimistic check the MT-1.6-04 risk note asks for. All optional at the
  schema level so an Owner override (which has no session or generation)
  can post with ``{}``; the *service* enforces presence for agent
  callers — an omitted generation must never act as a wildcard.
* ``LeaseRecord`` — Section 8.6's example JSON, field for field.
* ``WorkQuery`` — Section 9.2's ``role`` + filters for
  ``GET /projects/{pid}/work``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from rest_framework import serializers

from apps.core.pagination import MAX_PAGE_SIZE
from apps.core.serializers import StrictSerializerMixin
from apps.tasks.models import Task, TaskPriority
from apps.tasks.serializers import TaskSerializer


class ClaimRequestSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """``POST /tasks/{id}/claim`` input (Section 10.5 claim_task)."""

    session_id = serializers.CharField(
        max_length=255,
        help_text="Bridge-issued session id (G-18) — the lease's identity half.",
    )
    worker_agent_id = serializers.CharField(
        max_length=255,
        help_text="Human-readable worker label (Section 7.2 worker_agent_id; "
        "self-declared and spoofable — a label only, G-18).",
    )
    role = serializers.ChoiceField(
        choices=("coder", "auditor"),
        required=False,
        default="coder",
        help_text="Section 10.5 claim_task role input (coder default, "
        "auditor). Request intent only: the token's scopes gate first "
        "(Section 12.2) and the state decides inside the lock — coder "
        "claims only `pending` (T4), auditor only `to_be_audited` (T11) "
        "— a mismatch answers ROLE_NOT_PERMITTED (MT-3.3-01).",
    )


class ReleaseRequestSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """``POST /tasks/{id}/release`` input (ADR-012 fencing carrier)."""

    session_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_null=True,
        default=None,
        help_text="Lease-holding session id — required for agent callers; "
        "omitted for the Owner override.",
    )
    lease_generation = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
        default=None,
        help_text="Fencing generation from the claim response (Section 8.6) — "
        "required for agent callers; a stale value answers LEASE_EXPIRED.",
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
        help_text="Free-text reason recorded on the T6 Transition row's note "
        "(Section 10.5 release_task input).",
    )
    version = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
        default=None,
        help_text="Optional FR-TSK-06 optimistic check: when present, a stale "
        "value answers VERSION_CONFLICT.",
    )


class LeaseRecordSerializer(serializers.Serializer[Any]):
    """The Section 8.6 lease JSON — the stored claim record, as documented."""

    task_id = serializers.CharField()
    assigned_agent = serializers.CharField()
    session_id = serializers.CharField()
    role = serializers.CharField()
    lease_generation = serializers.IntegerField()
    lease_acquired_at = serializers.DateTimeField(allow_null=True)
    lease_expires_at = serializers.DateTimeField(allow_null=True)
    lease_hard_cap_at = serializers.DateTimeField(allow_null=True)
    last_checkpoint = serializers.DateTimeField(allow_null=True)
    failure_retry_count = serializers.IntegerField()


def lease_record_payload(task: Task) -> dict[str, Any]:
    """Build the Section 8.6 record from a claimed task + its policy.

    ``lease_hard_cap_at`` is ``lease_acquired_at`` +
    ``lease_max_total_minutes`` (Section 7.2 policy, default 240) — the
    deadline the extension formula clamps against (Section 8.6).
    """
    policy = task.project.agent_policy
    acquired = task.lease_acquired_at
    return {
        "task_id": task.pk,
        "assigned_agent": task.worker_agent_id or "",
        "session_id": task.worker_session_id or "",
        "role": task.claimed_role or "",
        "lease_generation": task.lease_generation,
        "lease_acquired_at": acquired,
        "lease_expires_at": task.lease_expires_at,
        "lease_hard_cap_at": (
            acquired + timedelta(minutes=policy.lease_max_total_minutes)
            if acquired is not None
            else None
        ),
        "last_checkpoint": task.last_checkpoint_at,
        "failure_retry_count": task.failure_retry_count,
    }


class RulesBlockSerializer(serializers.Serializer[Any]):
    """Section 10.6 rules block: standard rules + project rules appended."""

    standard_rules = serializers.ListField(child=serializers.CharField())
    project_rules = serializers.CharField(allow_blank=True)


class ClaimResponseSerializer(serializers.Serializer[Any]):
    """Section 9.3 step 6: task details, lease record, rules block."""

    task = TaskSerializer()
    lease = LeaseRecordSerializer()
    rules_block = RulesBlockSerializer()


class WorkQuerySerializer(serializers.Serializer[Any]):
    """``GET /projects/{pid}/work`` query parameters (Section 9.2)."""

    role = serializers.ChoiceField(
        choices=("coder", "auditor"),
        required=False,
        default="coder",
        help_text="Which offer list to read: coder → pending (default); "
        "auditor → to_be_audited (T11's audit claim takes it — "
        "MT-3.3-01).",
    )
    priority = serializers.ChoiceField(
        choices=TaskPriority.choices,
        required=False,
        help_text="FR-TSK-05 priority filter (single value).",
    )
    cursor = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Opaque cursor from the previous next_cursor; valid only "
        "with the same role/priority (pagination.md rule 1).",
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text=f"Items per page (default 25, maximum {MAX_PAGE_SIZE}; "
        "values above are clamped).",
    )
