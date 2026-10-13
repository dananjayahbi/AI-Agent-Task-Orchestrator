"""MT-1.11-03 — the multipart upload endpoint.

Run with ``pytest backend/tests/attachments/test_upload_endpoint.py
-v``. The suite proves the MT's acceptance criteria against the real
route:

* a valid multipart upload from an authenticated Owner answers 201 with
  the FR-ATT-03 descriptor at status ``uploaded`` (FR-ATT-07), stored
  through the MT-1.11-01 abstraction under the content key;
* invalid payloads answer the canonical envelope: 415
  ``ATTACHMENT_UNSUPPORTED_FORMAT`` (sniffing), 400
  ``VALIDATION_ERROR`` (limits/malformed), 404 ``TASK_NOT_FOUND``;
* replaying the same ``Idempotency-Key`` creates no second attachment
  (Section 9.2); same bytes without the header de-duplicate onto the
  existing record (200, one object);
* the pipeline enqueue seam exists and is exercised (the documented
  no-op; MT-1.12-01 completes it);
* the caller cell: Owner-only — agents/devices/anonymous refused.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.attachments.models import TaskAttachment
from apps.attachments.services import set_enqueue_seam
from apps.attachments.storage import content_key, hash_bytes
from apps.tasks.models import TaskState

from .helpers import (
    ELF_BYTES,
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

UPLOAD_URL = "/api/v1/tasks/{task_id}/attachments"


@pytest.fixture(autouse=True)
def media_root(tmp_path: Path) -> Iterator[Path]:
    """Every upload in this suite lands in an isolated media root."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture(autouse=True)
def capture_enqueue() -> Iterator[list[str]]:
    """Record every pipeline-seam invocation (reset after each test)."""
    calls: list[str] = []
    set_enqueue_seam(calls.append)
    yield calls
    set_enqueue_seam(None)


@pytest.fixture
def project() -> Any:
    """One active project."""
    return make_project()


@pytest.fixture
def task(project: Any) -> Any:
    """One pending task on that project."""
    return make_task(project)


def _post(client: APIClient, task_id: str, **kwargs: Any) -> Any:
    """One multipart POST to the upload route."""
    return client.post(
        UPLOAD_URL.format(task_id=task_id),
        {"file": upload(PNG_BYTES, name="photo.png", content_type="image/png"), **kwargs},
        format="multipart",
    )


# --- happy path ---------------------------------------------------------------


def test_owner_upload_answers_201_with_the_uploaded_descriptor(
    task: Any, media_root: Path, capture_enqueue: list[str]
) -> None:
    """Acceptance: valid multipart from Owner → descriptor, status uploaded."""
    owner = owner_client()
    response = _post(owner, task.pk)
    assert response.status_code == 201, response.content

    body: dict[str, Any] = response.json()
    assert body["task_id"] == task.pk
    assert body["filename"] == "photo.png"
    assert body["mime_type"] == "image/png"
    assert body["size"] == len(PNG_BYTES)
    assert body["is_image"] is True
    assert body["processing_status"] == "uploaded"  # FR-ATT-07
    assert body["token_count"] is None  # FR-ATT-03: null until WP-1.12
    assert body["short_description"] is None

    # Stored through the abstraction, under the content key, inside the root.
    digest = hash_bytes(PNG_BYTES)
    stored = media_root / content_key(digest)
    assert stored.read_bytes() == PNG_BYTES

    # One record, actor recorded (Section 9.6 actor-ref convention).
    row = TaskAttachment.objects.get(pk=body["id"])
    assert row.uploaded_by is not None

    # The enqueue seam ran exactly once, with the stored row's id (the
    # MT-1.11-03 acceptance: the hook exists and is exercised).
    assert capture_enqueue == [str(row.pk)]


def test_uploaded_descriptor_never_leaks_storage_key_or_digest(task: Any) -> None:
    """The descriptor is the FR-ATT-03 shape — nothing about keys (9.5)."""
    owner = owner_client()
    body: dict[str, Any] = _post(owner, task.pk).json()
    assert set(body) == {
        "id",
        "task_id",
        "filename",
        "mime_type",
        "size",
        "is_image",
        "processing_status",
        "token_count",
        "short_description",
        "created_at",
    }


def test_pdf_upload_records_non_image(task: Any) -> None:
    """Documents land with ``is_image`` false (the 9.5 pipeline split)."""
    owner = owner_client()
    response = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(PDF_BYTES, name="spec.pdf", content_type="application/pdf")},
        format="multipart",
    )
    assert response.status_code == 201, response.content
    assert response.json()["is_image"] is False


# --- rejection paths (canonical codes only, Section 20.4 item 5) -------------


def test_disguised_type_answers_415_unsupported_format(task: Any) -> None:
    """ELF bytes named .png: content sniffing decides, never the extension."""
    owner = owner_client()
    response = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(ELF_BYTES, name="malware.png", content_type="image/png")},
        format="multipart",
    )
    assert response.status_code == 415
    assert envelope_code(response) == "ATTACHMENT_UNSUPPORTED_FORMAT"
    assert TaskAttachment.objects.count() == 0


@override_settings(ATTACHMENT_MAX_FILE_BYTES=64)
def test_oversize_answers_400_validation_error(task: Any) -> None:
    """Over the (configured) per-file cap: VALIDATION_ERROR, nothing stored."""
    owner = owner_client()
    payload = PNG_BYTES + b"\x00" * 128
    response = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(payload, name="big.png", content_type="image/png")},
        format="multipart",
    )
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"
    assert TaskAttachment.objects.count() == 0


def test_missing_file_part_answers_400(task: Any) -> None:
    """No ``file`` part: VALIDATION_ERROR (the documented input shape)."""
    owner = owner_client()
    response = owner.post(UPLOAD_URL.format(task_id=task.pk), {}, format="multipart")
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"


def test_unknown_task_answers_404_task_not_found(project: Any) -> None:
    """The resource-owning code, straight from WP-1.4's helper."""
    owner = owner_client()
    response = owner.post(
        "/api/v1/tasks/PID00001-T999/attachments",
        {"file": upload(PNG_BYTES, name="photo.png", content_type="image/png")},
        format="multipart",
    )
    assert response.status_code == 404
    assert envelope_code(response) == "TASK_NOT_FOUND"


# --- idempotency (Section 9.2) and de-duplication (Section 9.5) ---------------


def test_idempotency_replay_creates_no_second_attachment(
    task: Any, media_root: Path, capture_enqueue: list[str]
) -> None:
    """Same key + same upload: the original response replays, one record."""
    owner = owner_client()
    headers = {"Idempotency-Key": "upload-retry-1"}
    first = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(PNG_BYTES, name="photo.png", content_type="image/png")},
        format="multipart",
        headers=headers,
    )
    assert first.status_code == 201, first.content

    second = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(PNG_BYTES, name="photo.png", content_type="image/png")},
        format="multipart",
        headers=headers,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert TaskAttachment.objects.count() == 1
    # One enqueue: the replay never re-executed the upload.
    assert len(capture_enqueue) == 1
    # One stored object, exactly the content key (media_root exercised).
    assert (media_root / content_key(hash_bytes(PNG_BYTES))).is_file()
    assert len([path for path in media_root.rglob("*") if path.is_file()]) == 1


def test_same_bytes_without_key_de_duplicate_onto_one_record(
    task: Any, media_root: Path, capture_enqueue: list[str]
) -> None:
    """Section 19 acceptance: duplicate uploads map to one record/object."""
    owner = owner_client()
    first = _post(owner, task.pk)
    second = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(PNG_BYTES, name="copy.png", content_type="image/png")},
        format="multipart",
    )
    assert first.status_code == 201
    assert second.status_code == 200  # the recorded dedupe response shape
    assert second.json()["id"] == first.json()["id"]
    assert TaskAttachment.objects.count() == 1
    assert len([path for path in media_root.rglob("*") if path.is_file()]) == 1


def test_different_bytes_create_a_second_record(task: Any, media_root: Path) -> None:
    """Different content: two records, two objects (content addressing)."""
    owner = owner_client()
    _post(owner, task.pk)
    other = PDF_BYTES + b"% more"
    response = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(other, name="spec.pdf", content_type="application/pdf")},
        format="multipart",
    )
    assert response.status_code == 201
    assert TaskAttachment.objects.count() == 2
    assert len([path for path in media_root.rglob("*") if path.is_file()]) == 2


# --- the caller cell: Owner only (Section 9.2) --------------------------------


def test_agent_token_is_refused(task: Any, project: Any) -> None:
    """Agents read, never upload (MT-1.11-03 out-of-scope note)."""
    owner = owner_client()
    agent = agent_client(owner, project.pk)
    response = _post(agent, task.pk)
    assert response.status_code == 403
    assert envelope_code(response) == "ROLE_NOT_PERMITTED"
    assert TaskAttachment.objects.count() == 0


def test_anonymous_is_refused(task: Any) -> None:
    """No credential: AUTH_REQUIRED (Section 9.2 envelope)."""
    response = APIClient().post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(PNG_BYTES, name="photo.png", content_type="image/png")},
        format="multipart",
    )
    assert response.status_code == 401
    assert envelope_code(response) == "AUTH_REQUIRED"


def test_cross_project_agent_token_is_refused_before_the_role_cell(task: Any, project: Any) -> None:
    """ADR-004 zero-bleed: a PID00002 token on a PID00001 route."""
    owner = owner_client()
    other = make_project(pid="PID00002")
    foreign = agent_client(owner, other.pk)
    response = _post(foreign, task.pk)
    assert response.status_code == 403
    assert envelope_code(response) == "AUTH_FORBIDDEN_PROJECT"


# --- archived/completed tasks may still receive uploads -----------------------


def test_completed_task_still_accepts_uploads(task: Any) -> None:
    """Section 9.5 gates *deletion* on completion, not upload — recorded."""
    task.state = TaskState.COMPLETED
    task.save(update_fields=["state"])
    owner = owner_client()
    assert _post(owner, task.pk).status_code == 201
