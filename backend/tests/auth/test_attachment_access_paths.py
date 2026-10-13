"""MT-1.15-04 — negative token paths and role read cells on the attachment surface.

The WP-1.12/1.13/1.14 attachment endpoints are Section 9.2's newest access
paths ("Owner / Agent (read)"). The positive caller cells, the cross-project
denial and the missing-credential case already live in the adopted suites —
``tests/test_authorization_matrix.py``'s WP-1.11/WP-1.14 landing cases and
``tests/attachments/`` — so this module carries only the cut MT-1.15-04 names
and nothing re-tests what they already prove (Section 19.6):

* the rest of MT-1.2-07's negative-path quartet — **malformed**, **unknown
  (wrong-key)** and **expired** tokens — on all five attachment routes, all
  answering the catalog ``AUTH_REQUIRED`` (missing-credential is the adopted
  suites' case);
* the **auditor** and **merge-executor** read cells the §9.2 column prints:
  every agent role reads list/detail/content in its own project (the content
  route answers its catalog ``ATTACHMENT_NOT_READY`` 409 for admitted callers
  — the hermetic suite's documented branch, so passing the permission cell is
  visible without running the pipeline).

Run: ``pytest backend/tests/auth/test_attachment_access_paths.py -v``.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken
from apps.core.errors import ATTACHMENT_NOT_READY, AUTH_REQUIRED, ROLE_NOT_PERMITTED
from tests import test_authorization_matrix as adopted
from tests.attachments import helpers

PID = "PID00001"

#: The five Section 9.2 attachment routes, concrete for PID00001-T001; the
#: id-shaped ones are filled with the fixture's real attachment id.
ACCESS_ROUTES: tuple[tuple[str, str], ...] = (
    ("POST", f"/api/v1/tasks/{PID}-T001/attachments"),
    ("GET", f"/api/v1/tasks/{PID}-T001/attachments"),
    ("GET", "/api/v1/attachments/{id}"),
    ("GET", "/api/v1/attachments/{id}/content?format=auto"),
    ("DELETE", "/api/v1/attachments/{id}"),
)


@pytest.fixture
def owner_client(db: None) -> APIClient:
    return helpers.owner_client("wp115-authz-owner")


@pytest.fixture
def task(db: None) -> Any:
    return helpers.make_task(helpers.make_project(pid=PID), index=1)


@pytest.fixture
def attachment_id(owner_client: APIClient, task: Any, tmp_path: Path) -> str:
    """One real uploaded row through the endpoint, stored under tmp media."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        created = owner_client.post(
            f"/api/v1/tasks/{task.pk}/attachments",
            {
                "file": SimpleUploadedFile(
                    "wp115.png",
                    helpers.png_bytes(),
                    content_type="image/png",
                )
            },
            format="multipart",
        )
    assert created.status_code == 201, created.content
    return str(created.json()["id"])


def _agent(owner_client: APIClient, role: str) -> tuple[APIClient, str, str]:
    """One project-scoped agent token for ``role``: (client, id, plaintext)."""
    response = owner_client.post("/api/v1/tokens/agent", {"project_id": PID, "scopes": [role]})
    assert response.status_code == 201, response.content
    body = response.json()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + str(body["token"]))
    return client, str(body["id"]), str(body["token"])


def _request(client: APIClient, method: str, path: str, headers: dict[str, str]) -> Any:
    if method == "POST":
        return client.post(path, {}, headers=headers)
    if method == "DELETE":
        return client.delete(path, headers=headers)
    return client.get(path, headers=headers)


def test_malformed_unknown_and_expired_tokens_answer_auth_required(
    owner_client: APIClient, attachment_id: str, db: None
) -> None:
    """The quartet's uncovered three shapes, on every attachment access path.

    MT-1.2-07 established these shapes on the tokens surface; the adopted
    attachment suites cover the missing-credential member here. Authentication
    runs before scope, role or body parsing, so all three shapes answer the
    same catalog code on every route.
    """
    plain = APIClient()
    expired, _expired_id, _expired_token = _agent(owner_client, "coder")
    ApiToken.objects.filter(pk=_expired_id).update(expires_at=timezone.now() - timedelta(seconds=1))
    shapes: tuple[tuple[str, APIClient, dict[str, str]], ...] = (
        ("malformed", plain, {"Authorization": "Bearer"}),
        ("unknown (wrong-key)", plain, {"Authorization": "Bearer " + "e" * 64}),
        ("expired", expired, {}),
    )
    for method, template in ACCESS_ROUTES:
        path = template.format(id=attachment_id)
        for label, client, headers in shapes:
            response = _request(client, method, path, headers)
            assert response.status_code == 401, (label, method, path, response.content)
            assert helpers.envelope_code(response) == AUTH_REQUIRED, (label, method, path)


def test_every_agent_role_reads_attachment_routes_in_its_own_project(
    owner_client: APIClient, task: Any, attachment_id: str, db: None
) -> None:
    """The §9.2 "Agent (read)" cell for every role — auditor included.

    The adopted matrix spot-checks coder (and a same-project decomposer) on
    these routes; the printed cell grants **every** project-scoped agent role
    read access, so this walks the full adopted role set. Upload and delete
    denials are the matrix's WP-1.11 loop — not repeated here.
    """
    for role in adopted.AGENT_ROLES:
        client, _token_id, _token = _agent(owner_client, role)

        listing = client.get(f"/api/v1/tasks/{task.pk}/attachments")
        assert listing.status_code == 200, (role, listing.content)

        detail = client.get(f"/api/v1/attachments/{attachment_id}")
        assert detail.status_code == 200, (role, detail.content)

        # Admitted callers pass the permission cell and hit the hermetic
        # catalog 409: the pipeline never ran, so the row is still
        # `uploaded` (the branch the matrix's WP-1.14 landing documents).
        content = client.get(f"/api/v1/attachments/{attachment_id}/content")
        assert content.status_code == 409, (role, content.content)
        assert helpers.envelope_code(content) == ATTACHMENT_NOT_READY, role


def test_owner_only_write_cells_survive_the_role_walk(
    owner_client: APIClient, task: Any, attachment_id: str, db: None
) -> None:
    """Direction check: the write halves refuse an admitted-read role too.

    The matrix's WP-1.11 loop already asserts every role's 403 on upload and
    delete; this single directional case pins that the *same* credential that
    just read (auditor) is still refused on the write halves — the read cell
    must never widen into one.
    """
    auditor, _token_id, _token = _agent(owner_client, "auditor")

    refused_upload = auditor.post(f"/api/v1/tasks/{task.pk}/attachments", {})
    assert refused_upload.status_code == 403
    assert helpers.envelope_code(refused_upload) == ROLE_NOT_PERMITTED

    refused_delete = auditor.delete(f"/api/v1/attachments/{attachment_id}")
    assert refused_delete.status_code == 403
    assert helpers.envelope_code(refused_delete) == ROLE_NOT_PERMITTED
