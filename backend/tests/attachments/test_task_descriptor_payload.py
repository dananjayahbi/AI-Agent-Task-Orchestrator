"""MT-1.14-01 — attachment descriptors embedded in task payloads (FR-ATT-03).

Run with ``pytest backend/tests/attachments/test_task_descriptor_payload.py -v``.

Proves:

* every task response embeds the FR-ATT-03 descriptor list — detail,
  create and list carry it (MT-1.14-01's recorded reading: every
  response that returns a task object);
* the embedded field set is **exactly** the MT-1.11-04 listing
  descriptor field set — one shape, asserted for parity rather than
  trusted to review (the G-01 drift-prevention risk note);
* no attachment content, derived text or storage path appears in a
  task payload (FR-ATT-03 "only attachment descriptors");
* ``token_count``/``short_description`` are null before ``ready`` and
  tolerate null after degradation without breaking serialization
  (MT-1.13-05's empty case).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.attachments.models import TaskAttachment
from apps.attachments.serializers import AttachmentSerializer

from .helpers import (
    MARKDOWN_BYTES,
    make_attachment,
    make_project,
    make_task,
    owner_client,
    process_ready,
)

pytestmark = pytest.mark.django_db

TASK_URL = "/api/v1/tasks/{task_id}"
TASKS_URL = "/api/v1/projects/{pid}/tasks"
ATTACHMENT_DETAIL = "/api/v1/attachments/{attachment_id}"

#: The descriptor field set MT-1.11-04 locked (test_descriptor_listing).
DESCRIPTOR_FIELDS = {
    "id",
    "task_id",
    "filename",
    "mime_type",
    "size",
    "is_image",
    "processing_status",
    "failure_reason",
    "token_count",
    "short_description",
    "created_at",
}


@pytest.fixture(autouse=True)
def media_root(tmp_path: Path) -> Any:
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def task() -> Any:
    return make_task(make_project())


@pytest.fixture
def owner() -> APIClient:
    return owner_client()


def _descriptor(owner: APIClient, attachment: TaskAttachment) -> dict[str, Any]:
    """The same attachment's listing descriptor — the parity baseline."""
    response = owner.get(ATTACHMENT_DETAIL.format(attachment_id=attachment.pk))
    assert response.status_code == 200, response.content
    return cast(dict[str, Any], response.json())


# --- the embedded shape (FR-ATT-03) ------------------------------------------


def test_task_detail_embeds_descriptors_with_the_listing_field_set(
    owner: APIClient, task: Any
) -> None:
    """One shape across listing and task payloads (MT-1.14-01 risk note)."""
    attachment = make_attachment(task, MARKDOWN_BYTES, name="notes.md")
    body = cast(dict[str, Any], owner.get(TASK_URL.format(task_id=task.pk)).json())

    assert body["attachments"] and len(body["attachments"]) == 1
    embedded = body["attachments"][0]
    assert set(embedded) == DESCRIPTOR_FIELDS
    assert set(embedded) == set(_descriptor(owner, attachment))  # parity, asserted


def test_create_and_list_task_responses_also_carry_descriptors(owner: APIClient, task: Any) -> None:
    """Every response that returns a task object embeds them (recorded)."""
    attachment = make_attachment(task, MARKDOWN_BYTES, name="notes.md")

    created = owner.post(
        TASKS_URL.format(pid=task.project_id),
        {
            "title": "New task",
            "description": "d",
            "acceptance_criteria": ["c"],
            "target_scope": ["src/**"],
            "test_command": "pytest -q",
            "priority": "medium",
        },
    )
    assert created.status_code == 201, created.content
    assert created.json()["attachments"] == []

    listed = owner.get(f"/api/v1/projects/{task.project_id}/tasks")
    assert listed.status_code == 200
    row = next(item for item in listed.json()["results"] if item["id"] == task.pk)
    assert row["attachments"][0]["id"] == str(attachment.pk)


def test_payload_carries_no_content_fields_or_storage_path(owner: APIClient, task: Any) -> None:
    """FR-ATT-03: descriptors only — content stays lazy (FR-ATT-04).

    The bounded extractive ``short_description`` is *descriptor* data by
    FR-ATT-03's own field list; what must never appear is content
    itself: the field set carries no transcript/markdown/content member
    (asserted via the locked descriptor set) and no storage path leaks.
    """
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    body = cast(dict[str, Any], owner.get(TASK_URL.format(task_id=task.pk)).json())
    embedded = body["attachments"][0]

    assert embedded["token_count"] == attachment.token_estimate  # the pipeline's number
    assert set(embedded) == DESCRIPTOR_FIELDS  # no content/ocr/markdown member
    assert attachment.storage_key not in str(body)  # no storage path (Section 12.4)
    assert attachment.sha256 not in str(body)  # no raw integrity data either


# --- nullable semantics (MT-1.11-04 / MT-1.13-05 tolerance) ------------------


def test_nulls_before_ready_and_after_degradation_serialize_cleanly(
    owner: APIClient, task: Any
) -> None:
    """Null token count/description before ready; tolerance after degradation."""
    pending = make_attachment(task, MARKDOWN_BYTES, name="later.md")
    embedded = cast(dict[str, Any], owner.get(TASK_URL.format(task_id=task.pk)).json())[
        "attachments"
    ][0]
    assert embedded["token_count"] is None
    assert embedded["short_description"] is None

    # OCR-only degradation (MT-1.13-05): empty summary stays null, not "".
    # (Distinct bytes: same-task uploads de-duplicate by checksum — 9.5.)
    ready = process_ready(task, b"# Second doc\n\nMore text.\n", name="done.md")
    TaskAttachment.objects.filter(pk=ready.pk).update(description="")
    embedded_ready = {
        item["id"]: item
        for item in cast(dict[str, Any], owner.get(TASK_URL.format(task_id=task.pk)).json())[
            "attachments"
        ]
    }
    assert embedded_ready[str(ready.pk)]["short_description"] is None
    assert embedded_ready[str(pending.pk)]["short_description"] is None


def test_embedded_descriptors_match_the_shared_serializer_component() -> None:
    """The OpenAPI component and the payload builder agree field-for-field."""
    field_set = set(AttachmentSerializer().fields)
    assert field_set == DESCRIPTOR_FIELDS
