"""MT-1.11-04 — attachment descriptor listing (id, filename, size, status).

Run with ``pytest backend/tests/attachments/test_descriptor_listing.py
-v``. The suite proves the MT's acceptance criteria against the real
routes:

* both ``GET /tasks/{id}/attachments`` and ``GET /attachments/{id}``
  return descriptors with at least ``id``, ``filename``, ``size``,
  ``processing_status`` (Section 19 WP-1.11; FR-ATT-03/07);
* ``token_count`` and ``short_description`` exist and are null before
  the pipeline runs (FR-ATT-03 field shape fixed now);
* listing is cursor-paginated per the WP-0.5 conventions with stable
  ``(-created_at, -id)`` ordering — every row exactly once;
* cross-project agent access answers ``AUTH_FORBIDDEN_PROJECT`` and the
  caller cell matches the Section 12.2 matrix (agent: read own
  project); soft-deleted rows never appear.
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

from apps.attachments.models import ProcessingStatus, TaskAttachment

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
DETAIL_URL = "/api/v1/attachments/{attachment_id}"

DESCRIPTOR_FIELDS = {
    "id",
    "task_id",
    "filename",
    "mime_type",
    "size",
    "is_image",
    "processing_status",
    "failure_reason",  # WP-1.12 addition (MT-1.12-07): FR-ATT-07 visible reason
    "token_count",
    "short_description",
    "created_at",
}


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
    """Upload one file and return its descriptor."""
    response = client.post(
        LIST_URL.format(task_id=task_id),
        {"file": upload(content, name=name, content_type=None)},
        format="multipart",
    )
    assert response.status_code in (200, 201), response.content
    return cast(dict[str, Any], response.json())


# --- descriptor shape (FR-ATT-03/07; MT-1.11-04 acceptance) ------------------


def test_detail_returns_the_full_descriptor(owner: APIClient, task: Any) -> None:
    """``GET /attachments/{id}``: the locked field set, values correct."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    response = owner.get(DETAIL_URL.format(attachment_id=body["id"]))
    assert response.status_code == 200
    detail: dict[str, Any] = response.json()
    assert set(detail) == DESCRIPTOR_FIELDS
    assert detail["id"] == body["id"]
    assert detail["size"] == len(PNG_BYTES)
    assert detail["processing_status"] == ProcessingStatus.UPLOADED


def test_pipeline_fields_are_null_before_ready(owner: APIClient, task: Any) -> None:
    """FR-ATT-03: token count and short description exist, null, until WP-1.12."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    assert body["token_count"] is None
    assert body["short_description"] is None


def test_pipeline_fields_surface_when_filled(owner: APIClient, task: Any) -> None:
    """The shape is fixed now; WP-1.12 only fills it (MT-1.11-04 risk)."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    TaskAttachment.objects.filter(pk=body["id"]).update(
        token_estimate=42, description="a screenshot of a form"
    )
    detail: dict[str, Any] = owner.get(DETAIL_URL.format(attachment_id=body["id"])).json()
    assert detail["token_count"] == 42
    assert detail["short_description"] == "a screenshot of a form"


def test_unknown_attachment_answers_400_validation_error(owner: APIClient) -> None:
    """No attachment not-found code exists — the recorded generic mapping."""
    response = owner.get(DETAIL_URL.format(attachment_id="0" * 32))
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"


def test_malformed_attachment_id_answers_400(owner: APIClient) -> None:
    """Boundary validation (Section 7.3 style) on the UUID."""
    response = owner.get(DETAIL_URL.format(attachment_id="not-a-uuid"))
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"


# --- listing shape and cursor pagination (WP-0.5 conventions) ----------------


def test_listing_shape_and_newest_first_order(owner: APIClient, task: Any) -> None:
    """The two-member envelope; newest first (created_at, then id)."""
    first = _upload(owner, task.pk, PDF_BYTES, "a.pdf")
    second = _upload(owner, task.pk, PNG_BYTES, "b.png")
    # The host wall clock ticks coarsely (~5-15 ms): two uploads inside one
    # tick share created_at and the documented (-created_at, -id) tiebreak
    # then legitimately outranks insertion order. Pin the first row strictly
    # older so "newest first" is observable regardless of clock granularity.
    second_row = TaskAttachment.objects.get(pk=second["id"])
    TaskAttachment.objects.filter(pk=first["id"]).update(
        created_at=second_row.created_at - timedelta(seconds=5)
    )

    response = owner.get(LIST_URL.format(task_id=task.pk))
    assert response.status_code == 200
    envelope: dict[str, Any] = response.json()
    assert set(envelope) == {"results", "next_cursor"}
    results = envelope["results"]
    assert [row["id"] for row in results] == [second["id"], first["id"]]
    assert envelope["next_cursor"] is None  # end of list
    for row in results:
        assert set(row) == DESCRIPTOR_FIELDS


def test_cursor_reaches_every_row_exactly_once(owner: APIClient, task: Any) -> None:
    """Pagination.md: continuation visits each row once, none skipped."""
    ids = [
        _upload(owner, task.pk, PDF_BYTES + bytes([index]), f"f{index}.pdf")["id"]
        for index in range(5)
    ]

    seen: list[str] = []
    cursor: str | None = None
    for _ in range(10):  # hard stop against a cursor bug looping forever
        url = LIST_URL.format(task_id=task.pk)
        if cursor is not None:
            url += f"?cursor={cursor}"
        envelope: dict[str, Any] = owner.get(url).json()
        seen.extend(row["id"] for row in envelope["results"])
        cursor = envelope["next_cursor"]
        if cursor is None:
            break
    assert cursor is None
    assert len(seen) == 5
    assert set(seen) == set(ids)


def test_page_size_clamps_to_the_documented_maximum(owner: APIClient, task: Any) -> None:
    """Default 25, maximum 100 — pagination.md documented defaults."""
    for index in range(3):
        _upload(owner, task.pk, PDF_BYTES + bytes([index]), f"f{index}.pdf")
    response = owner.get(LIST_URL.format(task_id=task.pk) + "?page_size=1000")
    envelope: dict[str, Any] = response.json()
    assert len(envelope["results"]) == 3  # clamped, not rejected


def test_malformed_cursor_answers_400(owner: APIClient, task: Any) -> None:
    """A mangled cursor is a client error from the closed catalog (rule 1)."""
    response = owner.get(LIST_URL.format(task_id=task.pk) + "?cursor=not-base64-!!")
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"


def test_empty_task_returns_an_empty_page(owner: APIClient, task: Any) -> None:
    """An empty list is an empty page, not an error."""
    response = owner.get(LIST_URL.format(task_id=task.pk))
    assert response.status_code == 200
    assert response.json() == {"results": [], "next_cursor": None}


def test_listing_excludes_soft_deleted_rows(owner: APIClient, task: Any) -> None:
    """MT-1.11-05 interplay: deleted records vanish from list *and* detail."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    TaskAttachment.objects.filter(pk=body["id"]).update(deleted_at=timezone.now())

    envelope: dict[str, Any] = owner.get(LIST_URL.format(task_id=task.pk)).json()
    assert envelope["results"] == []
    response = owner.get(DETAIL_URL.format(attachment_id=body["id"]))
    assert response.status_code == 400  # unknown-to-the-API (recorded mapping)


# --- authorization: the Section 9.2 read cell (Owner / Agent) -----------------


def test_agent_reads_its_own_project(owner: APIClient, project: Any, task: Any) -> None:
    """The bridge's future reader: an agent token reads own-project descriptors."""
    _upload(owner, task.pk, PNG_BYTES, "photo.png")
    agent = agent_client(owner, project.pk)
    listing = agent.get(LIST_URL.format(task_id=task.pk))
    assert listing.status_code == 200
    assert len(listing.json()["results"]) == 1


def test_cross_project_agent_answers_auth_forbidden_project(
    owner: APIClient, project: Any, task: Any
) -> None:
    """Section 12.1: cross-project leakage is refused at the scope guard."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    other = make_project(pid="PID00002")
    foreign = agent_client(owner, other.pk)

    listing = foreign.get(LIST_URL.format(task_id=task.pk))
    assert listing.status_code == 403
    assert envelope_code(listing) == "AUTH_FORBIDDEN_PROJECT"

    detail = foreign.get(DETAIL_URL.format(attachment_id=body["id"]))
    assert detail.status_code == 403
    assert envelope_code(detail) == "AUTH_FORBIDDEN_PROJECT"


def test_device_is_refused_on_reads(owner: APIClient, project: Any, task: Any) -> None:
    """Devices are not in the Section 9.2 Attachments caller cell."""
    body = _upload(owner, task.pk, PNG_BYTES, "photo.png")
    registration = owner.post("/api/v1/devices", {"platform": "android", "push_token": "apns-wp11"})
    assert registration.status_code == 201, registration.content
    device = APIClient()
    device.credentials(HTTP_AUTHORIZATION=f"Bearer {registration.json()['token']}")
    listing = device.get(LIST_URL.format(task_id=task.pk))
    assert listing.status_code == 403
    assert envelope_code(listing) == "ROLE_NOT_PERMITTED"
    detail = device.get(DETAIL_URL.format(attachment_id=body["id"]))
    assert detail.status_code == 403
    assert envelope_code(detail) == "ROLE_NOT_PERMITTED"


def test_anonymous_is_refused(owner: APIClient, task: Any) -> None:
    """AUTH_REQUIRED on both read routes (Section 9.2 envelope)."""
    listing = APIClient().get(LIST_URL.format(task_id=task.pk))
    assert listing.status_code == 401
    assert envelope_code(listing) == "AUTH_REQUIRED"


def test_unknown_task_on_listing_answers_404(owner: APIClient) -> None:
    """WP-1.4's resource-owning code flows through the shared route."""
    response = owner.get(LIST_URL.format(task_id="PID00001-T999"))
    assert response.status_code == 404
    assert envelope_code(response) == "TASK_NOT_FOUND"
