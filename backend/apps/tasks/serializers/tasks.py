"""Request/response contracts for the Tasks row (Section 9.2; MT-1.4-03).

Shapes mirror the OpenAPI operations:

* ``TaskSerializer`` — the read model: every Section 7.2 field, all
  read-only (server-managed; writability is defined by the two input
  serializers below, never by the representation).
* ``TaskCreateSerializer`` — ``POST /projects/{pid}/tasks``: exactly the
  FR-TSK-02 create inputs (title, description, acceptance criteria,
  target scope, test command, priority). ``state``/``version``/``id``/
  ``project_id`` are **not declared** — the strict mixin turns them into
  ``VALIDATION_ERROR`` instead of silently dropping them (the MT-1.4-03
  writable-field allowlist half of "PATCH must not become a
  state-changing backdoor").
* ``TaskUpdateSerializer`` — ``PATCH /tasks/{id}``: the same FR-TSK-02
  editable fields, all optional, plus the **required** ``version`` the
  client saw (FR-TSK-06's compare-and-swap token — validated here,
  consumed by ``services.tasks.update_task``, never written as data).
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.attachments.models import TaskAttachment
from apps.attachments.serializers import AttachmentSerializer
from apps.attachments.services import attachment_payload
from apps.core.pagination import MAX_PAGE_SIZE
from apps.core.serializers import StrictSerializerMixin

from ..models import Task, TaskDependency, TaskPriority, TaskState
from ..services.tasks import validate_target_scope_globs

# The FR-TSK-02 editable set (MT-1.4-03 risk note: an explicit allowlist,
# tested). Everything Section 7.2 adds beyond it — state, version (as a
# *value*), lease/worker fields, merge_status, archived_at, counters —
# stays server-owned; `version` appears below only as the CAS token.
EDITABLE_FIELDS: tuple[str, ...] = (
    "title",
    "description",
    "acceptance_criteria",
    "target_scope",
    "test_command",
    "priority",
)


class TaskSerializer(serializers.Serializer[Any]):
    """GET representation of a task — Section 7.2 fields, in plan order.

    One documented addition beyond the 7.2 table: ``attachments`` — the
    FR-ATT-03 descriptor list (MT-1.14-01; descriptors only, content
    stays lazy behind the Section 9.2 content endpoint).
    """

    id = serializers.CharField(
        read_only=True,
        help_text="{PID}-T{index} (Section 7.3); server-assigned, immutable.",
    )
    project_id = serializers.CharField(
        read_only=True,
        help_text="Section 7.2 project_id FK — never changes (7.4 rule 4).",
    )
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(
        read_only=True,
        help_text="Markdown description (FR-TSK-02).",
    )
    acceptance_criteria = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    target_scope = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
        help_text="Repo-relative path globs (Section 12.3).",
    )
    test_command = serializers.CharField(read_only=True)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, read_only=True)
    state = serializers.ChoiceField(
        choices=TaskState.choices,
        read_only=True,
        help_text="Canonical G-01 state (ADR-010); draft on create (T1).",
    )
    version = serializers.IntegerField(
        read_only=True,
        help_text="FR-TSK-06: incremented on every change; PATCH echoes it.",
    )
    worker_agent_id = serializers.CharField(
        allow_null=True, read_only=True, help_text="Lease holder (WP-1.6)."
    )
    worker_session_id = serializers.CharField(
        allow_null=True, read_only=True, help_text="Bridge session (G-18)."
    )
    claimed_role = serializers.CharField(
        allow_null=True, read_only=True, help_text="coder | auditor | null."
    )
    lease_acquired_at = serializers.DateTimeField(allow_null=True, read_only=True)
    lease_expires_at = serializers.DateTimeField(allow_null=True, read_only=True)
    last_checkpoint_at = serializers.DateTimeField(allow_null=True, read_only=True)
    failure_retry_count = serializers.IntegerField(read_only=True)
    audit_retry_count = serializers.IntegerField(
        read_only=True,
        help_text="WP-3.3 / Section 8.2 T12: audit leases released by expiry "
        "(kept separate from failure_retry_count — Section 8.3 invariant 1).",
    )
    attempt_number = serializers.IntegerField(read_only=True)
    audit_required = serializers.BooleanField(
        read_only=True,
        help_text="Copied from the project policy at creation (Section 7.2).",
    )
    review_reason = serializers.CharField(
        allow_null=True, read_only=True, help_text="Section 8.4 enum | null."
    )
    latest_feedback = serializers.CharField(
        read_only=True,
        help_text="Section 7.2: text from auditor/human — the T16 "
        "request-changes note shown to the next coder through "
        "get_task_details (Section 10.5; MT-3.6-03); empty until the "
        "first note, newest note wins.",
    )
    merge_status = serializers.CharField(
        read_only=True, help_text="none | pending | merging | merged | conflict | failed."
    )
    archived_at = serializers.DateTimeField(
        allow_null=True,
        read_only=True,
        help_text="Soft-archive marker; archived tasks stay readable (7.3).",
    )
    created_by = serializers.CharField(allow_null=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    depends_on = serializers.SerializerMethodField(
        help_text=(
            "Section 7.1 N:N relation (FR-TSK-07): the task ids this task "
            "waits on, ordered by id. Server-managed — written through the "
            "`depends_on` field of POST/PATCH (replace-the-set), read here."
        )
    )

    def get_depends_on(self, obj: Task) -> list[str]:
        """Edges for *obj* — reuse the prefetch cache when one was primed."""
        cache = getattr(obj, "_prefetched_objects_cache", None) or {}
        if "dependency_edges" in cache:
            edges = obj.dependency_edges.all()
            return sorted(edge.depends_on_id for edge in edges)
        return list(
            TaskDependency.objects.filter(task=obj)
            .order_by("depends_on_id")
            .values_list("depends_on_id", flat=True)
        )

    attachments = serializers.SerializerMethodField(
        help_text=(
            "FR-ATT-03 attachment descriptors — one per live attachment: "
            "`id`, `filename`, `size`, `token_count`, `short_description` "
            "(the MT-1.11-04 field set, one shape with the listing "
            "endpoints). Descriptors only — attachment content and derived "
            "text are never embedded; they are fetched on demand from "
            "GET /attachments/{id}/content (FR-ATT-03's lazy model, "
            "FR-ATT-04). `token_count` and `short_description` are null "
            "before `ready` and after OCR-only degradation. Newest first. "
            "Every response that returns a task object carries them "
            "(MT-1.14-01's recorded reading)."
        )
    )

    @extend_schema_field(AttachmentSerializer(many=True))
    def get_attachments(self, obj: Task) -> list[dict[str, Any]]:
        """FR-ATT-03 descriptors for *obj* — reuse the prefetch when primed.

        Built by :func:`apps.attachments.services.attachment_payload` —
        the single descriptor-shape source shared with the upload and
        listing endpoints (MT-1.11-04; MT-1.14-01's drift-prevention
        risk note).
        """
        cache = getattr(obj, "_prefetched_objects_cache", None) or {}
        if "attachments" in cache:
            rows = obj.attachments.all()
        else:
            rows = TaskAttachment.objects.filter(task=obj)
        return [attachment_payload(row) for row in rows.order_by("-created_at", "-pk")]


class TaskCreateSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """POST /projects/{pid}/tasks body — the FR-TSK-02 create inputs only."""

    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Markdown (FR-TSK-02); editable afterwards via PATCH.",
    )
    acceptance_criteria = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Acceptance-criteria strings (Section 7.2).",
    )
    target_scope = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Repo-relative globs, validated on creation (Section 12.3).",
    )
    test_command = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
    )
    priority = serializers.ChoiceField(
        choices=TaskPriority.choices,
        required=False,
        default=TaskPriority.MEDIUM,
        help_text="FR-TSK-05; default medium (documented default — not a plan fact).",
    )
    depends_on = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Task ids this task waits on (Section 7.1 relation; FR-TSK-07). "
            "Same-project ids only; existence, self and cycles validated — "
            "a refusal rolls the whole create back (VALIDATION_ERROR)."
        ),
    )

    def validate_target_scope(self, value: list[Any]) -> list[str]:
        """Section 12.3 boundary rule — the shared service-layer helper."""
        return validate_target_scope_globs(value)


class TaskUpdateSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """PATCH /tasks/{id} body — FR-TSK-02 fields + the FR-TSK-06 version."""

    version = serializers.IntegerField(
        min_value=1,
        help_text="The version the client saw (required — FR-TSK-06). A stale "
        "value answers VERSION_CONFLICT; a match applies and increments.",
    )
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    acceptance_criteria = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    target_scope = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    test_command = serializers.CharField(required=False, allow_blank=True, max_length=500)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, required=False)
    depends_on = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Replace-the-set dependency write (MT-1.4-05): the payload "
            "becomes the full set — omit to leave it untouched, `[]` clears "
            "it. Validated under the version check, same transaction."
        ),
    )

    def validate_target_scope(self, value: list[Any]) -> list[str]:
        """Same Section 12.3 rule as create — one helper, no drift."""
        return validate_target_scope_globs(value)


class TaskListEnvelopeSerializer(serializers.Serializer[Any]):
    """pagination.md envelope: exactly ``results`` + ``next_cursor``."""

    results = TaskSerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque cursor for the next page; null = end of list.",
    )


class TaskListQuerySerializer(serializers.Serializer[Any]):
    """GET /projects/{pid}/tasks query parameters (MT-1.4-04).

    ``state`` is a *repeated* parameter (``?state=draft&state=pending`` —
    the OpenAPI ``form``/``explode`` default for array query params);
    ``include_archived``'s name is the flag MT-1.4-04 asked to confirm in
    the changelog (MT-1.4-06 owns the archive behavior it feeds).
    """

    cursor = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Opaque cursor from the previous page's next_cursor; valid "
        "only with the same filters it was issued under (pagination.md rule 1).",
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text=(
            f"Items per page (default 25, maximum {MAX_PAGE_SIZE}; values "
            "above the maximum are clamped — pagination.md documented "
            "defaults, same per-endpoint choice as GET /projects)."
        ),
    )
    state = serializers.ListField(
        child=serializers.ChoiceField(choices=TaskState.choices),
        required=False,
        help_text="Canonical states to include; repeat for several "
        "(?state=draft&state=pending). Unknown values are VALIDATION_ERROR.",
    )
    priority = serializers.ChoiceField(
        choices=TaskPriority.choices,
        required=False,
        help_text="FR-TSK-05 priority filter (single value).",
    )
    include_archived = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Include soft-archived tasks; default false — archived "
        "tasks are hidden from boards by default (Section 8.2 T19).",
    )


__all__ = [
    "EDITABLE_FIELDS",
    "TaskCreateSerializer",
    "TaskListEnvelopeSerializer",
    "TaskListQuerySerializer",
    "TaskSerializer",
    "TaskUpdateSerializer",
]
