"""One live conformance run against the Compose stack (MT-2.11-01; Section 18).

The "run the runner once against the local Compose stack" acceptance step:
a full stdio run of :func:`tests.conformance.runner.run_conformance` against
the real seeded backend - exit contract, all ten Section 10.5 tools, all four
Section 10.7 prompts, and a report whose matrix cells match Section 10.9.

Gated exactly like the other live suites (``ORCHESTRATOR_BRIDGE_LIVE_TESTS=1``
plus a reachable ``wp16-pg``; skipped otherwise). The test seeds its *own*
conformance task (target scope ``conformance/**``) and one ready text-OCR
image attachment through a dedicated ``manage.py shell`` invocation, so it
neither depends on nor disturbs the shared live seed used by the core-tools
and auditor-chain live tests. Text-path packaging only on the live side
(no storage bytes); the vision packaging is pinned by the hermetic harness
self-tests.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests import _live_backend
from tests.conformance.runner import RunnerConfig, run_conformance
from tests.git_fixtures import make_repo

pytestmark = pytest.mark.skipif(
    _live_backend.skip_reason() is not None,
    reason=_live_backend.skip_reason() or "unreachable",
)

#: Seeds PID00007-T005 with a ``conformance/**`` target scope plus one ready
#: image attachment (plain OCR text: the delivery path is what must add the
#: untrusted banner exactly once; idempotent re-runs: update_or_create +
#: state reset).
_SEED_CONFORMANCE = """
from apps.projects.models import Project
from apps.tasks.models import Task, TaskState
from apps.tasks.models.dependencies import TaskDependency
from apps.attachments.models import TaskAttachment, ProcessingStatus
import uuid
project = Project.objects.get(pk="PID00007")
task_id = "PID00007-T005"
Task.objects.get_or_create(
    id=task_id,
    project=project,
    defaults={"title": "Bridge IT: conformance runner task", "state": TaskState.PENDING},
)
Task.objects.filter(id=task_id).update(
    state=TaskState.PENDING,
    target_scope=["conformance/**"],
    test_command="pytest -q",
    worker_agent_id=None,
    worker_session_id=None,
    claimed_role=None,
    lease_acquired_at=None,
    lease_expires_at=None,
    archived_at=None,
)
# A pre-existing row (e.g. a draft from another live test) may carry
# dependency edges that would hide the task from the coder offer list.
TaskDependency.objects.filter(task_id=task_id).delete()
Project.objects.filter(pk="PID00007", task_counter__lt=5).update(task_counter=5)
attachment_id = str(uuid.uuid4())
# Delete-then-create: the shared live DB may hold rows from earlier or
# concurrent seeded runs; the conformance task needs exactly one attachment.
TaskAttachment.objects.filter(task_id=task_id, filename="conformance-shot.png").delete()
TaskAttachment.objects.create(
    id=attachment_id,
    task_id=task_id,
    filename="conformance-shot.png",
    mime_type="image/png",
    size_bytes=256,
    is_image=True,
    storage_key="conformance/placeholder",
    sha256="0" * 64,
    processing_status=ProcessingStatus.READY,
    ocr_text="The screenshot shows a task board with one pending card.",
    layout_caption="Mock UI screen: a board with columns.",
    uploaded_by="conformance-seed",
)
print("CONFORMANCE_SEED", task_id, attachment_id)
"""


#: The shared live DB may carry a patch artifact from a previous seeded run
#: whose re-seed is not yet idempotent (a concurrent live suite's known
#: duplicate-key crash on ``artifact_one_per_resolution_kind``); deleting the
#: rows lets the seed recreate exactly what its own flow stores.
_PRECLEAN = """
from apps.tasks.models import TaskArtifact, ArtifactKind
TaskArtifact.objects.filter(kind=ArtifactKind.PATCH).delete()
print("CONFORMANCE_PRECLEAN done")
"""


@pytest.fixture(scope="module")
def live_conformance_backend() -> Iterator[tuple[_live_backend.LiveBackend, str]]:
    """One migrated, seeded backend plus the seeded conformance task id."""
    preclean = _live_backend._run_backend(  # noqa: SLF001 - shared live harness seam
        ["python", "manage.py", "shell", "-c", _PRECLEAN], timeout=120
    )
    if preclean.returncode != 0:
        pytest.skip(
            f"live database not resettable for the conformance run: {preclean.stderr[-400:]}"
        )
    backend = _live_backend.start_live_backend()
    try:
        completed = _live_backend._run_backend(  # noqa: SLF001 - shared live harness seam
            ["python", "manage.py", "shell", "-c", _SEED_CONFORMANCE], timeout=120
        )
        task_id = None
        for line in completed.stdout.splitlines():
            if line.startswith("CONFORMANCE_SEED "):
                task_id = line.split()[1]
        if task_id is None:
            pytest.fail(
                f"conformance seed printed no marker: "
                f"stdout={completed.stdout!r} stderr={completed.stderr[-800:]!r}"
            )
        yield backend, task_id
    finally:
        _live_backend.stop_live_backend(backend)


def test_live_conformance_run_matches_section_10_9(
    live_conformance_backend: tuple[_live_backend.LiveBackend, str], tmp_path: Path
) -> None:
    backend, task_id = live_conformance_backend
    coder_token = backend.tokens[0]
    auditor_token = backend.tokens[1]
    decomposer_token = backend.decomposer_token
    assert decomposer_token is not None

    manifest = {
        "schema_version": 1,
        "project_id": backend.project_id,
        "project_name": "Bridge IT Project",
        "orchestrator_api": backend.api_base_url,
        "default_branch": "main",
        "auto_branch_prefix": f"feat/{backend.project_id}-",
        "audit_required_default": True,
    }
    repo = make_repo(
        tmp_path / "live-conformance-repo",
        {"orchestrator.json": json.dumps(manifest), "README.md": "# live conformance\n"},
    )
    report_path = tmp_path / "conformance-report.json"
    config = RunnerConfig(
        manifest_path=repo / "orchestrator.json",
        repo_path=repo,
        report_path=report_path,
        project_id=backend.project_id,
        transport="stdio",
        coder_token=coder_token,
        auditor_token=auditor_token,
        decomposer_token=decomposer_token,
        spool_dir=tmp_path / "spool",
        capability=None,  # the real default client: unknown, text-safe
        client_label="Custom agent harness (live Compose run)",
        coder_task_id=task_id,
        cwd=Path(__file__).resolve().parent.parent,
    )
    report = run_conformance(config)
    report.write(report_path)

    assert report.passed, report.summary()
    assert len(report.tools_exercised) == 10, report.tools_exercised
    assert report.prompts_surfaced == [
        "orchestrator:start_work",
        "orchestrator:checkpoint",
        "orchestrator:submit_for_audit",
        "orchestrator:audit",
    ]
    row = report.matrix_row()
    assert list(row) == ["Transport", "Prompts surfaced", "Images in tool results", "Notes"]
    assert row["Transport"] == "STDIO"
    assert row["Prompts surfaced"].startswith("yes")
    # Unknown-capability session: text-safe packaging with the untrusted banner.
    assert report.text_only_path_seen and not report.vision_path_seen
    # Live error paths observed, all from the Section 9.2 catalog.
    assert "TASK_ALREADY_CLAIMED" in report.observed_error_codes
    assert report_path.exists()
    artifact = json.loads(report_path.read_text(encoding="utf-8"))
    assert artifact["matrix"] == row
    assert artifact["passed"] is True
