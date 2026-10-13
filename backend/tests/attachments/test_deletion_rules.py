"""MT-1.11-05 — deletion rules and retention hooks.

Run with ``pytest backend/tests/attachments/test_deletion_rules.py
-v``. The suite proves the MT's acceptance criteria against the real
routes and hooks:

* ``DELETE /attachments/{id}``: Owner only; refused (409
  ``TASK_STATE_CONFLICT``) on completed/archived tasks — Section 16.3's
  "never by user action on completed tasks"; allowed earlier with the
  record marked deleted;
* deleting an attachment never removes stored bytes another
  de-duplicated record references (content-key reference counting);
* the retention hook applies the archive-plus-grace rule (Section 12.4;
  OQ-10 default 30 days, configurable) with the boundary proven on
  both sides, and cleans orphaned objects (Section 9.9);
* derived data drops independently of the original (Section 9.5).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.attachments.models import TaskAttachment
from apps.attachments.retention import (
    drop_derived_data,
    purge_archived_attachments,
)
from apps.attachments.storage import content_key, hash_bytes
from apps.tasks.models import TaskState

from .helpers import (
    PDF_BYTES,
    PNG_BYTES,
    agent_client,
    envelope_code,
    make_project,
    make_task,
    owner_client,
    upload,
)

pytestmark = pytest.mark.django_db

LIST_URL = "/api/v1/tasks/{task_id}/attachments"
DELETE_URL = "/api/v1/attachments/{attachment_id}"


@pytest.fixture(autouse=True)
def media_root(tmp_path: Path) -> Iterator[Path]:
    """Uploads land in an isolated media root."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def project() -> Any:
    """One active project."""
    return make_project()


@pytest.fixture
def task(project: Any) -> Any:
    """One pending task."""
    return make_task(project)


@pytest.fixture
def owner() -> APIClient:
    """A logged-in owner session."""
    return owner_client()


def _upload(client: APIClient, task_id: str, content: bytes, name: str) -> dict[str, Any]:
    """Upload one file, return its descriptor."""
    response = client.post(
        LIST_URL.format(task_id=task_id),
        {"file": upload(content, name=name)},
        format="multipart",
    )
    assert response.status_code in (200, 201), response.content
    return cast(dict[str, Any], response.json())


def _stored_files(root: Path) -> list[Path]:
    """Every regular file under the media root."""
    return [path for path in root.rglob("*") if path.is_file()]


# --- the DELETE rule matrix by task state (Section 16.3) ----------------------


def test_delete_before_completion_soft_deletes_and_removes_bytes(
    owner: APIClient, task: Any, media_root: Path
) -> None:
    """The allowed case: record marked deleted, unreferenced bytes removed."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    response = owner.delete(DELETE_URL.format(attachment_id=body["id"]))
    assert response.status_code == 200, response.content
    payload: dict[str, Any] = response.json()
    assert payload["id"] == body["id"]
    assert payload["deleted_at"] is not None  # soft delete marker (recorded)

    row = TaskAttachment.objects.get(pk=body["id"])
    assert row.deleted_at is not None
    assert _stored_files(media_root) == []  # no other reference: bytes gone
    # Gone from the API surface too (list and detail — MT-1.11-04 interplay).
    assert owner.get(LIST_URL.format(task_id=task.pk)).json()["results"] == []


def test_delete_on_completed_task_is_refused(owner: APIClient, task: Any) -> None:
    """Section 16.3: the user never hard-deletes a completed task's files."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    task.state = TaskState.COMPLETED
    task.save(update_fields=["state"])

    response = owner.delete(DELETE_URL.format(attachment_id=body["id"]))
    assert response.status_code == 409
    assert envelope_code(response) == "TASK_STATE_CONFLICT"
    row = TaskAttachment.objects.get(pk=body["id"])
    assert row.deleted_at is None  # nothing was marked or removed


def test_delete_on_archived_task_is_refused(owner: APIClient, task: Any) -> None:
    """Archived is the other half of the Section 16.3 rule."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    task.archived_at = timezone.now()
    task.save(update_fields=["archived_at"])

    response = owner.delete(DELETE_URL.format(attachment_id=body["id"]))
    assert response.status_code == 409
    assert envelope_code(response) == "TASK_STATE_CONFLICT"


def test_delete_is_owner_only(owner: APIClient, project: Any, task: Any) -> None:
    """The Section 9.2 caller cell: DELETE is Owner, not Agent."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    agent = agent_client(owner, project.pk)
    response = agent.delete(DELETE_URL.format(attachment_id=body["id"]))
    assert response.status_code == 403
    assert envelope_code(response) == "ROLE_NOT_PERMITTED"
    assert TaskAttachment.objects.get(pk=body["id"]).deleted_at is None


def test_delete_by_foreign_project_agent_is_scope_refused(owner: APIClient, task: Any) -> None:
    """ADR-004 zero-bleed: the scope guard answers before the role cell."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    other = make_project(pid="PID00002")
    foreign = agent_client(owner, other.pk)
    response = foreign.delete(DELETE_URL.format(attachment_id=body["id"]))
    assert response.status_code == 403
    assert envelope_code(response) == "AUTH_FORBIDDEN_PROJECT"


def test_unknown_attachment_delete_answers_400(owner: APIClient) -> None:
    """The recorded generic mapping (no attachment not-found code)."""
    response = owner.delete(DELETE_URL.format(attachment_id="0" * 32))
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"


# --- content-key reference counting (the MT's sharp edge) --------------------


def test_shared_key_bytes_survive_one_deletion(
    owner: APIClient, task: Any, media_root: Path
) -> None:
    """Two records, one key (per-task dedupe is impossible post-dedupe,
    so this proves the cross-task sharing path): the first deletion keeps
    the bytes because another live record references them."""
    first = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    # A second task, same bytes: two records, one stored object.
    other_task = make_task(task.project, 2)
    second = _upload(owner, other_task.pk, PNG_BYTES, "copy.png")
    assert first["id"] != second["id"]
    assert len(_stored_files(media_root)) == 1  # content addressing dedup

    response = owner.delete(DELETE_URL.format(attachment_id=first["id"]))
    assert response.status_code == 200
    assert TaskAttachment.objects.get(pk=first["id"]).deleted_at is not None
    # The surviving record still has its bytes (reference counting).
    assert len(_stored_files(media_root)) == 1

    # Removing the last reference removes the object.
    assert owner.delete(DELETE_URL.format(attachment_id=second["id"])).status_code == 200
    assert _stored_files(media_root) == []


def test_delete_is_idempotent_at_the_record(owner: APIClient, task: Any) -> None:
    """A soft-deleted row is unknown to the API — no second decision."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    assert owner.delete(DELETE_URL.format(attachment_id=body["id"])).status_code == 200
    again = owner.delete(DELETE_URL.format(attachment_id=body["id"]))
    assert again.status_code == 400  # unknown to the surface (recorded)
    assert envelope_code(again) == "VALIDATION_ERROR"


# --- the retention hook (Sections 9.9, 12.4; OQ-10 default) ------------------


def _archive_and_age(task: Any, days: float) -> None:
    """Archive *task* with an ``archived_at`` *days* before now."""
    task.archived_at = timezone.now() - timedelta(days=days)
    task.save(update_fields=["archived_at"])


def test_retention_purges_after_the_grace_period(
    owner: APIClient, task: Any, media_root: Path
) -> None:
    """OQ-10 default: archive + 30 days → the hook purges records and bytes."""
    _upload(owner, task.pk, PNG_BYTES, "photo.png")
    _archive_and_age(task, 31)

    outcome = purge_archived_attachments()
    assert outcome.records_deleted == 1
    assert outcome.objects_removed == 1
    assert outcome.tasks_processed == 1
    assert TaskAttachment.objects.count() == 0
    assert _stored_files(media_root) == []


def test_retention_retains_exactly_at_the_boundary(owner: APIClient, task: Any) -> None:
    """The boundary is inclusive-at-retain: archive + grace == now keeps.

    The instant is pinned on both sides (the hook takes ``now``) so the
    boundary is exact, not a sleep race.
    """
    _upload(owner, task.pk, PNG_BYTES, "photo.png")
    from django.conf import settings

    moment = timezone.now()
    task.archived_at = moment - timedelta(days=settings.ATTACHMENT_RETENTION_GRACE_DAYS)
    task.save(update_fields=["archived_at"])

    outcome = purge_archived_attachments(now=moment)
    assert outcome.records_deleted == 0
    assert TaskAttachment.objects.count() == 1


def test_retention_retains_active_and_recently_archived(owner: APIClient, project: Any) -> None:
    """Active tasks and fresh archives are untouched (the rule's shape)."""
    active = make_task(project, 1)
    fresh = make_task(project, 2)
    archived_old = make_task(project, 3)
    for task in (active, fresh, archived_old):
        _upload(owner, task.pk, PNG_BYTES + task.pk.encode(), f"{task.pk}.png")
    _archive_and_age(fresh, 1)
    _archive_and_age(archived_old, 40)

    outcome = purge_archived_attachments()
    assert outcome.records_deleted == 1  # only the old archive
    assert TaskAttachment.objects.filter(task=archived_old).count() == 0
    assert TaskAttachment.objects.filter(task=active).count() == 1
    assert TaskAttachment.objects.filter(task=fresh).count() == 1


def test_retention_grace_is_configurable(owner: APIClient, task: Any) -> None:
    """The Section 9.10 group overrides the OQ-10 default."""
    _upload(owner, task.pk, PNG_BYTES, "photo.png")
    _archive_and_age(task, 2)
    with override_settings(ATTACHMENT_RETENTION_GRACE_DAYS=1):
        outcome = purge_archived_attachments()
    assert outcome.records_deleted == 1


def test_retention_keeps_shared_keys_alive(
    owner: APIClient, project: Any, media_root: Path
) -> None:
    """Reference counting inside the purge: a shared object survives."""
    old = make_task(project, 1)
    live = make_task(project, 2)
    _upload(owner, old.pk, PNG_BYTES, "a.png")
    _upload(owner, live.pk, PNG_BYTES, "b.png")  # same bytes → one object
    _archive_and_age(old, 40)

    outcome = purge_archived_attachments()
    assert outcome.records_deleted == 1
    assert outcome.objects_removed == 0  # still referenced by the live task
    assert len(_stored_files(media_root)) == 1


def test_retention_is_idempotent(owner: APIClient, task: Any) -> None:
    """A crashed sweep resumes cleanly: a second run finds nothing."""
    _upload(owner, task.pk, PNG_BYTES, "photo.png")
    _archive_and_age(task, 40)
    first = purge_archived_attachments()
    second = purge_archived_attachments()
    assert first.records_deleted == 1
    assert second.records_deleted == 0
    assert second.objects_removed == 0


def test_retention_includes_soft_deleted_records(
    owner: APIClient, task: Any, media_root: Path
) -> None:
    """Soft-deleted rows ride the same archive purge (bookkeeping cleanup)."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    owner.delete(DELETE_URL.format(attachment_id=body["id"]))
    _archive_and_age(task, 40)

    outcome = purge_archived_attachments()
    assert outcome.records_deleted == 1  # the soft-deleted row is hard-removed
    assert TaskAttachment.objects.count() == 0


# --- derived data is droppable independently (Section 9.5) -------------------


def test_drop_derived_data_keeps_the_original(
    owner: APIClient, task: Any, media_root: Path
) -> None:
    """Derived columns clear; the stored original stays (re-creatable rule)."""
    body = _upload(owner, task.pk, PDF_BYTES, "spec.pdf")
    TaskAttachment.objects.filter(pk=body["id"]).update(
        ocr_text="page one text",
        extracted_markdown="# extracted",
        description="a spec",
        layout_caption="n/a",
        token_estimate=123,
        page_count=4,
    )
    row = TaskAttachment.objects.get(pk=body["id"])
    cleaned = drop_derived_data(row)

    cleaned.refresh_from_db()
    assert cleaned.ocr_text == ""
    assert cleaned.extracted_markdown == ""
    assert cleaned.description == ""
    assert cleaned.token_estimate is None
    assert cleaned.page_count is None
    # The original: record, key and bytes all intact (Section 9.5).
    assert cleaned.processing_status == row.processing_status
    assert cleaned.storage_key == content_key(hash_bytes(PDF_BYTES))
    assert len(_stored_files(media_root)) == 1
