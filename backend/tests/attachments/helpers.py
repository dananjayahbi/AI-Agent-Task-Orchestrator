"""Shared factories for the WP-1.11 attachment suites.

Not a test module (no ``test_`` prefix — the ``tests/wp15_helpers.py``
idiom): project/task rows, an owner-session client, an agent-token
client, and minimal valid payloads for every Section 9.5 allowlisted
type (built from real magic bytes so the sniffer sees genuine content).
"""

from __future__ import annotations

import io
import zipfile
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task, TaskState

PASSWORD = "wp11-tests-1!"  # pragma: allowlist secret

# --- minimal valid payloads per Section 9.5 allowlist -----------------------

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 16
WEBP_BYTES = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 8
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n%%EOF\n"
MARKDOWN_BYTES = b"# Heading\n\nSome **markdown** body.\n"
PLAINTEXT_BYTES = b"Just plain text.\n"
# Disguised type: executable bytes named .png (MT-1.11-02 acceptance).
ELF_BYTES = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 24


def docx_bytes() -> bytes:
    """A structurally valid DOCX: zip container with word/document.xml."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types/>',
        )
        archive.writestr("word/document.xml", '<?xml version="1.0"?><document/>')
    return buffer.getvalue()


def plain_zip_bytes() -> bytes:
    """A zip that is **not** a DOCX: no word/document.xml part inside."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "just a zip")
    return buffer.getvalue()


def upload(
    content: bytes,
    *,
    name: str = "file.bin",
    content_type: str | None = None,
) -> SimpleUploadedFile:
    """One multipart file part with the given bytes/name/declared type."""
    return SimpleUploadedFile(
        name, content, content_type=content_type or "application/octet-stream"
    )


# --- rows and clients --------------------------------------------------------


def make_project(*, pid: str = "PID00001") -> Project:
    """One active project row (deterministic id, direct insert)."""
    return Project.objects.create(
        id=pid,
        name=f"WP-1.11 {pid}",
        repo_path=f"/srv/repos/{pid.lower()}",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )


def make_task(project: Project, index: int = 1, **overrides: Any) -> Task:
    """One task row with a deterministic id (the allocator is WP-1.4's)."""
    payload: dict[str, Any] = {
        "id": f"{project.pk}-T{index:03d}",
        "project": project,
        "title": f"Task {index:03d}",
        "state": TaskState.PENDING,
    }
    payload.update(overrides)
    task = Task.objects.create(**payload)
    Project.objects.filter(pk=project.pk, task_counter__lt=index).update(task_counter=index)
    return task


def owner_client(username: str = "wp11-owner") -> APIClient:
    """A logged-in owner session (cookie transport)."""
    User.objects.create_user(username, None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


def agent_client(owner: APIClient, project_id: str) -> APIClient:
    """A plain client carrying one project-scoped agent bearer token."""
    response = owner.post("/api/v1/tokens/agent", {"project_id": project_id, "scopes": ["coder"]})
    assert response.status_code == 201, response.content
    payload: dict[str, Any] = response.json()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {payload['token']}")
    return client


def envelope_code(response: Any) -> str:
    """The catalog code of one standard envelope (five fields, asserted)."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])
