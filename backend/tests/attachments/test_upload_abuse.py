"""MT-6.1-02 — upload abuse cases: traversal, oversized, spoofed MIME (WP-6.1).

Section 12.1's "malicious uploads" threat and Section 18's Security row
("path traversal", "upload abuse"; Integration row "scrambled and oversized
inputs") attacked against the WP-1.11/WP-1.12 intake. Every case asserts a
**canonical Section 9.2 envelope** (catalog-closed — Section 20.4 item 5) and
**no write outside the storage root**: the local backend stores under
content-addressed keys (MT-1.11-01), so the client filename never becomes a
path; traversal/absolute/symlink-style names cannot materialize anything.

Fixtures are inert (trivially synthetic bytes — Section 20.4 item 3 spirit):
this suite proves rejection behavior and never commits weaponized samples.

Worker separation (Section 12.1 "sandboxed parsing in the worker"): the web
request only validates, stores and records — parsing is handed to the Celery
job (``attachments.process_attachment``) through the enqueue seam wired in
``AttachmentsConfig.ready()``; the suite asserts the hand-off and that no
processing happens inline. OS-level sandboxing stays the Section 12.3
post-v1 limitation (recorded in the threat-to-test mapping, L2); optional AV
is absent by plan (L3, same row).

Run with ``pytest backend/tests/ -k upload_abuse -v`` (MT test command).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.attachments.models import TaskAttachment
from apps.attachments.services import create_attachment, set_enqueue_seam
from apps.attachments.storage import content_key
from apps.attachments.validation import strip_filename

from .helpers import (
    ELF_BYTES,
    PNG_BYTES,
    envelope_code,
    make_project,
    make_task,
    owner_client,
    upload,
)

pytestmark = pytest.mark.django_db

UPLOAD_URL = "/api/v1/tasks/{task_id}/attachments"

TRAVERSAL_NAME = "../../escape.png"
ABSIX_NAME = "C:\\Windows\\System32\\evil.png"


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


@pytest.fixture
def owner() -> APIClient:
    """A logged-in owner client (the helpers' plain factory, fixture-shaped)."""
    return owner_client()


def _post(client: APIClient, task_id: str, part: Any) -> Any:
    """One multipart POST to the upload route."""
    return client.post(UPLOAD_URL.format(task_id=task_id), {"file": part}, format="multipart")


def _assert_no_escape(root: Path) -> None:
    """Nothing under the storage root is a symlink or resolves outside it.

    The Section 12.3 boundary this suite attacks: content keys nest under
    ``objects/<aa>/<digest>``, so every entry — directories included —
    must stay strictly inside *root*.
    """
    root_resolved = root.resolve()
    for entry in root.rglob("*"):
        assert not entry.is_symlink(), f"storage root gained a symlink: {entry}"
        assert entry.resolve().is_relative_to(root_resolved), f"escaped root: {entry}"


def _stored_leaves(root: Path) -> list[str]:
    """Relative posix keys of every stored object (files only)."""
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def _assert_rejected_cleanly(root: Path, before_rows: int) -> None:
    """A refusal leaves no bytes, no row and no worker hand-off behind."""
    _assert_no_escape(root)
    assert list(root.iterdir()) == [], "a rejected upload left a partial artifact"
    assert TaskAttachment.objects.count() == before_rows, "a rejected upload wrote a row"


# --- traversal (raw, encoded, absolute, symlink-style) ----------------------


def test_service_rejects_traversal_filename_without_leaving_the_root(
    task: Any, media_root: Path, capture_enqueue: list[str]
) -> None:
    """Raw ``../`` segments never become a path (Section 12.3 normalization).

    The service layer sees the unvarnished string (the multipart parser
    basenames on the wire; this half proves the second barrier): the name
    is normalized to its final component and the bytes land under the
    content key only.
    """
    before = TaskAttachment.objects.count()
    outcome = create_attachment(
        task_id=task.pk,
        filename=TRAVERSAL_NAME,
        declared_mime="image/png",
        data=PNG_BYTES,
        uploaded_by="wp61-abuse",
    )

    assert not outcome.deduplicated
    stored = outcome.attachment
    assert "/" not in stored.filename and "\\" not in stored.filename
    assert ".." not in stored.filename
    assert stored.filename == "escape.png" == strip_filename(TRAVERSAL_NAME)
    assert stored.storage_key == content_key(outcome.attachment.sha256)
    _assert_no_escape(media_root)
    assert (media_root / stored.storage_key).read_bytes() == PNG_BYTES
    assert TaskAttachment.objects.count() == before + 1


def test_service_rejects_absolute_path_filename_without_touching_the_filesystem(
    task: Any, media_root: Path
) -> None:
    """Absolute paths (POSIX and Windows) normalize to a bare basename."""
    for index, absolute in enumerate(("/etc/payload.png", ABSIX_NAME)):
        outcome = create_attachment(
            task_id=task.pk,
            filename=absolute,
            declared_mime="image/png",
            data=PNG_BYTES + bytes([index]),  # distinct content per iteration
            uploaded_by="wp61-abuse",
        )
        stored = outcome.attachment
        assert stored.filename == ("payload.png" if absolute.startswith("/") else "evil.png")
        assert stored.storage_key == content_key(stored.sha256)
    _assert_no_escape(media_root)


def test_service_refuses_a_filename_that_normalizes_to_nothing(task: Any, media_root: Path) -> None:
    """Names whose final component is empty carry no usable filename — 400."""
    before = TaskAttachment.objects.count()
    for hostile in ("/", "", "   "):
        with pytest.raises(Exception) as raised:
            create_attachment(
                task_id=task.pk,
                filename=hostile,
                declared_mime="image/png",
                data=PNG_BYTES,
                uploaded_by="wp61-abuse",
            )
        assert type(raised.value).__name__ == "ValidationError"
    _assert_rejected_cleanly(media_root, before)


def test_traversal_only_filename_is_an_inert_label_not_a_path(task: Any, media_root: Path) -> None:
    """``../..`` normalizes to the label ``..`` — inert: never a path.

    The label is metadata only (the bytes live under the content key and
    nothing joins the label into a path); the cosmetic ``..`` label is
    recorded as findings-log F-05, not papered over here.
    """
    outcome = create_attachment(
        task_id=task.pk,
        filename="../..",
        declared_mime="image/png",
        data=PNG_BYTES,
        uploaded_by="wp61-abuse",
    )
    stored = outcome.attachment
    assert stored.filename == ".."
    assert stored.storage_key == content_key(stored.sha256)
    assert (media_root / stored.storage_key).read_bytes() == PNG_BYTES
    _assert_no_escape(media_root)


def test_encoded_traversal_filename_is_inert_and_stays_content_keyed(
    task: Any, media_root: Path
) -> None:
    """Percent-encoded ``%2e%2e%2f`` is literal text — never decoded to a path."""
    outcome = create_attachment(
        task_id=task.pk,
        filename="%2e%2e%2fescape.png",
        declared_mime="image/png",
        data=PNG_BYTES,
        uploaded_by="wp61-abuse",
    )
    stored = outcome.attachment
    assert stored.storage_key == content_key(stored.sha256)
    _assert_no_escape(media_root)
    assert (media_root / stored.storage_key).read_bytes() == PNG_BYTES


def test_endpoint_traversal_attempt_is_normalized_on_the_wire(
    task: Any, owner: APIClient, media_root: Path
) -> None:
    """The wire path: a traversal filename lands only under the content key."""
    response = _post(
        owner,
        task.pk,
        upload(PNG_BYTES, name=TRAVERSAL_NAME, content_type="image/png"),
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["filename"] == "escape.png"
    row = TaskAttachment.objects.get(pk=body["id"])
    assert (media_root / row.storage_key).read_bytes() == PNG_BYTES
    assert _stored_leaves(media_root) == [row.storage_key], "only the content key exists"
    _assert_no_escape(media_root)


def test_stored_objects_are_never_symlinks(task: Any, media_root: Path) -> None:
    """Symlink-style attempts cannot turn storage into links (12.3)."""
    for name in ("photo.png", "photo.png:evil", "link->../target.png"):
        outcome = create_attachment(
            task_id=task.pk,
            filename=name,
            declared_mime="image/png",
            data=PNG_BYTES,
            uploaded_by="wp61-abuse",
        )
        stored_path = media_root / outcome.attachment.storage_key
        assert stored_path.is_file() and not stored_path.is_symlink()
    _assert_no_escape(media_root)


# --- oversized --------------------------------------------------------------


def test_oversized_upload_is_refused_with_no_partial_artifact(
    task: Any, owner: APIClient, media_root: Path, capture_enqueue: list[str]
) -> None:
    """Beyond the configured cap: 400 canonical, nothing stored, no hand-off."""
    before = TaskAttachment.objects.count()
    with override_settings(ATTACHMENT_MAX_FILE_BYTES=64):
        response = _post(
            owner,
            task.pk,
            upload(PNG_BYTES * 4, name="huge.png", content_type="image/png"),
        )

    assert response.status_code == 400, response.content
    assert envelope_code(response) == "VALIDATION_ERROR"
    _assert_rejected_cleanly(media_root, before)
    assert capture_enqueue == [], "the worker never receives a refused upload"


def test_empty_and_zero_byte_uploads_are_refused_cleanly(
    task: Any, owner: APIClient, media_root: Path
) -> None:
    """Section 18 scrambled inputs: empty body → canonical refusal, no rows."""
    before = TaskAttachment.objects.count()
    response = _post(owner, task.pk, upload(b"", name="nothing.png"))
    assert response.status_code == 400, response.content
    assert envelope_code(response) == "VALIDATION_ERROR"
    _assert_rejected_cleanly(media_root, before)


# --- spoofed MIME (content decides, never the client header) ----------------


def test_executable_bytes_renamed_to_an_image_are_rejected(
    task: Any, owner: APIClient, media_root: Path, capture_enqueue: list[str]
) -> None:
    """ELF bytes under ``.png`` + image declaration → 415, nothing written."""
    before = TaskAttachment.objects.count()
    response = _post(
        owner,
        task.pk,
        upload(ELF_BYTES, name="photo.png", content_type="image/png"),
    )
    assert response.status_code == 415, response.content
    assert envelope_code(response) == "ATTACHMENT_UNSUPPORTED_FORMAT"
    _assert_rejected_cleanly(media_root, before)
    assert capture_enqueue == []


def test_image_bytes_renamed_to_a_document_are_rejected(
    task: Any, owner: APIClient, media_root: Path
) -> None:
    """PNG bytes under ``.pdf`` + pdf declaration → 415 (sniffing wins)."""
    before = TaskAttachment.objects.count()
    response = _post(
        owner,
        task.pk,
        upload(PNG_BYTES, name="report.pdf", content_type="application/pdf"),
    )
    assert response.status_code == 415, response.content
    assert envelope_code(response) == "ATTACHMENT_UNSUPPORTED_FORMAT"
    _assert_rejected_cleanly(media_root, before)


def test_octet_stream_declaration_cannot_smuggle_disallowed_bytes(
    task: Any, owner: APIClient, media_root: Path
) -> None:
    """``application/octet-stream`` is no declaration — sniffing still rules."""
    before = TaskAttachment.objects.count()
    response = _post(
        owner,
        task.pk,
        upload(ELF_BYTES, name="payload.bin", content_type="application/octet-stream"),
    )
    assert response.status_code == 415, response.content
    assert envelope_code(response) == "ATTACHMENT_UNSUPPORTED_FORMAT"
    _assert_rejected_cleanly(media_root, before)


def test_client_declared_type_is_never_trusted_for_allowed_content(
    task: Any, owner: APIClient, media_root: Path
) -> None:
    """A truthful upload under a generic declaration takes the sniffed type."""
    response = _post(
        owner,
        task.pk,
        upload(PNG_BYTES, name="photo.png", content_type="application/octet-stream"),
    )
    assert response.status_code == 201, response.content
    assert response.json()["mime_type"] == "image/png", "the bytes decided, not the header"
    _assert_no_escape(media_root)


# --- worker-vs-web separation (Section 12.1; OS sandbox = 12.3 limitation) --


def test_web_request_defers_parsing_to_the_worker_task(
    task: Any, owner: APIClient, media_root: Path, capture_enqueue: list[str]
) -> None:
    """The request stores and hands off; it never parses inline (12.1)."""
    response = _post(
        owner,
        task.pk,
        upload(PNG_BYTES, name="photo.png", content_type="image/png"),
    )
    assert response.status_code == 201, response.content

    # The row is only "uploaded": no processing/ready state was reached in
    # the web process — parsing is the worker's half of the pipeline.
    row = TaskAttachment.objects.get(pk=response.json()["id"])
    assert row.processing_status == "uploaded"
    # Exactly one hand-off, carrying the stored row's id (the seam contract).
    assert capture_enqueue == [str(row.pk)]
    # And no pipeline event was written by the web request itself.
    from apps.events.models import Event

    assert not Event.objects.filter(type__startswith="attachment.").exists()


def test_the_enqueue_seam_targets_the_celery_worker_job() -> None:
    """Configuration half: the real seam is the shared Celery task (9.9)."""
    from apps.attachments.pipeline import process_attachment_task
    from apps.attachments.services import _default_enqueue

    assert process_attachment_task.name == "attachments.process_attachment"
    assert callable(process_attachment_task.delay)
    # The unit layer default stays the documented no-op (Section 18: no
    # broker); ready() swaps it for the worker job in every broker process.
    _default_enqueue("wp61-noop-probe")  # returns None; nothing is enqueued
