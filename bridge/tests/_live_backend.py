"""Real-backend harness for the WP-2.4 live tests (MT-2.4-07; NFR-01; Section 18).

Not a test module (no ``test_`` prefix). Spawns the **real backend** — Django
migrations + ASGI app over Uvicorn — against the local ``wp16-pg`` Postgres
(``docker start wp16-pg``) and the local Redis, seeds one project with agent
tokens and pending tasks, and hands the bridge tests a live ``/api/v1`` origin
to drive the real claim service through the HTTP boundary.

Gating (the protocol's "PG-gated bridge test" allowance): the suite only runs
when ``ORCHESTRATOR_BRIDGE_LIVE_TESTS=1`` **and** Postgres answers on the
configured port; otherwise tests skip with the exact start command in the
reason. Backend code is *subprocess-run* (``manage.py``/uvicorn), never
imported — the ADR/Appendix A boundary (``test_layout.py``) holds.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

#: The gate: opt-in env var (read at import — the conftest strips ambient
#: ORCHESTRATOR_* variables per test, but the subprocess env is built here).
LIVE_ENV_FLAG = "ORCHESTRATOR_BRIDGE_LIVE_TESTS"

#: Defaults named by the assignment: wp16-pg on 5434; Redis on its standard
#: loopback port. Both overridable for CI or another local stack. The
#: credentials are the compose dev container's documented locals — never a
#: production secret (Section 20.4 item 3).
DEFAULT_DATABASE_URL = (
    "postgresql://orchestrator:wp16-change-me@127.0.0.1:5434/"  # pragma: allowlist secret
    "orchestrator"
)
DEFAULT_CACHE_URL = "redis://127.0.0.1:6379/0"

#: Marker line the seed script prints; everything before it is Django noise.
SEED_MARKER = "BRIDGE_IT_SEED "

_MIGRATE_TIMEOUT_SECONDS = 300
_SERVER_START_TIMEOUT_SECONDS = 90

_SEED_SCRIPT = """
import hashlib, json, secrets
from apps.accounts.models import ApiToken, TokenKind, User
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task, TaskResolution, TaskState
from apps.tasks.services.patch_parse import parse_unified_diff
from apps.tasks.services.resolutions import store_patch_artifact

PID = "PID00007"
owner, _ = User.objects.get_or_create(username="bridge-it-owner", defaults={})
try:
    project = Project.objects.get(pk=PID)
except Project.DoesNotExist:
    project = Project.objects.create(
        id=PID,
        name="Bridge IT Project",
        repo_path="e:/bridge-it",
        default_branch="main",
        system_prompt_rules="Bridge IT rule: run the tests before submitting.",
        agent_policy=ProjectPolicy.objects.create(),
    )

def make_task(index, title):
    task_id = f"{PID}-T{index:03d}"
    Task.objects.filter(id=task_id).update(
        state=TaskState.PENDING,
        worker_agent_id=None,
        worker_session_id=None,
        claimed_role=None,
        lease_acquired_at=None,
        lease_expires_at=None,
        archived_at=None,
    )
    Task.objects.get_or_create(
        id=task_id, project=project, title=title, state=TaskState.PENDING
    )
    Project.objects.filter(pk=PID, task_counter__lt=index).update(task_counter=index)
    return task_id

tasks = [
    make_task(1, "Bridge IT: chain task"),
    make_task(2, "Bridge IT: two-bridge race task"),
    make_task(3, "Bridge IT: fifty-way race task"),
]

# MT-3.5-03/04: one to_be_audited task carrying its attempt-1 resolution and a
# *stored* clean patch artifact, so an independent auditor session can claim it
# (T11) and the Policy Engine can scan added lines (R5b) for a T13 approve. The
# coder session is fixed; the auditor session is bridge-minted and always
# differs, so the session half of the independence rule (G-20) passes.
CLEAN_PATCH = (
    "diff --git a/src/app.py b/src/app.py\\n"
    "index 1111111..2222222 100644\\n"
    "--- a/src/app.py\\n"
    "+++ b/src/app.py\\n"
    "@@ -1,1 +1,2 @@\\n"
    " context-line\\n"
    "+print('hello')\\n"
)
AUDIT_INDEX = 4
auditable_task_id = f"{PID}-T{AUDIT_INDEX:03d}"
coder_session = "sess-live-coder"
parsed = parse_unified_diff(CLEAN_PATCH)
_task, _created = Task.objects.get_or_create(
    id=auditable_task_id,
    project=project,
    defaults={
        "title": "Bridge IT: auditable task",
        "state": TaskState.TO_BE_AUDITED,
        "attempt_number": 1,
        "audit_required": True,
        "target_scope": ["src/**"],
        "test_command": "pytest -q",
    },
)
# Reset to a clean auditable baseline on every seed run (idempotent re-runs).
Task.objects.filter(id=auditable_task_id).update(
    state=TaskState.TO_BE_AUDITED,
    attempt_number=1,
    audit_required=True,
    target_scope=["src/**"],
    test_command="pytest -q",
    worker_agent_id=None,
    worker_session_id=None,
    claimed_role=None,
    lease_acquired_at=None,
    lease_expires_at=None,
    merge_status="none",
    review_reason=None,
    archived_at=None,
)
Project.objects.filter(pk=PID, task_counter__lt=AUDIT_INDEX).update(task_counter=AUDIT_INDEX)
resolution, _ = TaskResolution.objects.get_or_create(
    task_id=auditable_task_id,
    attempt_number=1,
    defaults={
        "branch_name": f"feat/{PID}-T{AUDIT_INDEX:03d}",
        "commit_sha": "0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        "execution_summary": "live auditor-flow seed submission",
        "submitted_by_session": coder_session,
        "changed_files": list(parsed.changed_files),
        "diff_summary": parsed.as_diff_summary(),
    },
)
# Store the patch body so R5(b) can scan added lines (stored artifact row).
# Idempotent re-runs: artifact_one_per_resolution_kind means a re-seed of the
# same resolution must not create a second patch artifact.
if not resolution.artifacts.filter(kind="patch").exists():
    store_patch_artifact(resolution, CLEAN_PATCH)

tokens = []
for _ in range(5):
    plaintext = "bridge-it-" + secrets.token_hex(24)
    ApiToken.objects.create(
        kind=TokenKind.AGENT,
        hash=hashlib.sha256(plaintext.encode("utf-8")).hexdigest(),
        user=owner,
        project_id=PID,
        scopes=["coder", "auditor"],
    )
    tokens.append(plaintext)
# MT-3.8-01/02: one decomposer-scoped token for the live draft-creation proof.
decomposer_token = "bridge-it-" + secrets.token_hex(24)
ApiToken.objects.create(
    kind=TokenKind.AGENT,
    hash=hashlib.sha256(decomposer_token.encode("utf-8")).hexdigest(),
    user=owner,
    project_id=PID,
    scopes=["decomposer"],
)
print(
    "BRIDGE_IT_SEED "
    + json.dumps(
        {
            "project_id": PID,
            "tasks": tasks,
            "tokens": tokens,
            "decomposer_token": decomposer_token,
            # MT-3.5-03/04: the to_be_audited task the live auditor chain claims.
            "auditable_task": auditable_task_id,
            "auditor_coder_session": coder_session,
        }
    )
)
"""


def live_enabled() -> bool:
    """Whether the operator opted into the live suite."""
    return os.environ.get(LIVE_ENV_FLAG) == "1"


def database_url() -> str:
    return os.environ.get("ORCHESTRATOR_BRIDGE_LIVE_DATABASE_URL", DEFAULT_DATABASE_URL)


def postgres_reachable(timeout: float = 3.0) -> bool:
    """Raw TCP probe of the configured Postgres endpoint."""
    parsed = urlparse(database_url())
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def skip_reason() -> str | None:
    """:class:`None` when the live stack is runnable, else the skip message."""
    if not live_enabled():
        return (
            f"live bridge suite is opt-in: set {LIVE_ENV_FLAG}=1 with "
            f"`docker start wp16-pg` (database: {database_url()})"
        )
    if shutil.which("uv") is None:
        return "live bridge suite needs uv on PATH"
    if not postgres_reachable():
        return (
            f"Postgres not reachable at {database_url()} — "
            "`docker start wp16-pg` (port 5434), then re-run"
        )
    return None


def _subprocess_env() -> dict[str, str]:
    """The ambient environment minus ORCHESTRATOR_* leakage, plus the stack.

    The dev settings module reads the canonical Section 9.10 names; the
    Secret key is a documented dev-only placeholder (never a real secret).
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith("ORCHESTRATOR_")}
    # Dev-only placeholder, never a real secret (Section 20.4 item 3).
    dev_secret = "bridge-it-dev-only-not-a-secret"  # pragma: allowlist secret
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "apps.core.settings.dev",
            "ORCHESTRATOR_DATABASE_URL": database_url(),
            "ORCHESTRATOR_CACHE_URL": os.environ.get(
                "ORCHESTRATOR_BRIDGE_LIVE_CACHE_URL", DEFAULT_CACHE_URL
            ),
            "ORCHESTRATOR_SECRET_KEY": dev_secret,
            # MT-3.5-03/04: the auditable seed stores a patch artifact, so the
            # media root must be a writable local dir (never the /media default,
            # which is not writable on every host).
            "ORCHESTRATOR_STORAGE_MEDIA_ROOT": str(Path(__file__).resolve().parent / ".live-media"),
        }
    )
    return env


def _run_backend(args: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [shutil.which("uv") or "uv", "run", "--directory", str(BACKEND_DIR), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        env=_subprocess_env(),
        cwd=str(BACKEND_DIR),
        check=False,
    )


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_for_health(
    origin: str, process: subprocess.Popen[str], timeout: float, log_path: Path
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            tail = (
                log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                if log_path.exists()
                else "(no log)"
            )
            raise RuntimeError(f"backend exited early (code {process.returncode})\n{tail}")
        try:
            with urllib.request.urlopen(f"{origin}/health/live", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    raise RuntimeError(f"backend did not become healthy at {origin} within {timeout}s")


@dataclass
class LiveBackend:
    """One running backend plus the seeded fixture data."""

    origin: str  # e.g. http://127.0.0.1:54321 — add /api/v1 for the client base
    project_id: str
    tasks: tuple[str, ...]
    tokens: tuple[str, ...]
    decomposer_token: str | None = None  # MT-3.8-02 live draft-creation proof
    auditable_task: str | None = None  # MT-3.5-03/04 to_be_audited chain task
    auditor_coder_session: str | None = None  # the seed's independent coder session
    process: subprocess.Popen[str] | None = None
    log_path: Path | None = None

    @property
    def api_base_url(self) -> str:
        return f"{self.origin}/api/v1"

    def healthy(self, timeout: float = 5.0) -> bool:
        """Cheap liveness probe — used to fail fast (with logs) when wedged."""
        try:
            with urllib.request.urlopen(f"{self.origin}/health/live", timeout=timeout) as response:
                status: int = response.status
                return status == 200
        except (urllib.error.URLError, OSError):
            return False

    def stdout_tail(self, lines: int = 40) -> str:
        """The captured uvicorn output — diagnostics for a wedged backend."""
        if self.log_path is None or not self.log_path.exists():
            return "(no backend output captured)"
        content = self.log_path.read_text(encoding="utf-8", errors="replace")
        return "\n".join(content.splitlines()[-lines:])


def start_live_backend() -> LiveBackend:
    """Migrate, seed, and boot the backend; the fixture tears it down."""
    migrate = _run_backend(
        ["python", "manage.py", "migrate", "--noinput"], timeout=_MIGRATE_TIMEOUT_SECONDS
    )
    if migrate.returncode != 0:
        raise RuntimeError(
            f"manage.py migrate failed:\n{migrate.stdout[-2000:]}\n{migrate.stderr[-2000:]}"
        )
    seeded = _run_backend(["python", "manage.py", "shell", "-c", _SEED_SCRIPT], timeout=120)
    if seeded.returncode != 0:
        raise RuntimeError(f"seed script failed:\n{seeded.stdout[-2000:]}\n{seeded.stderr[-2000:]}")
    seed_line = next(
        (line for line in reversed(seeded.stdout.splitlines()) if line.startswith(SEED_MARKER)),
        None,
    )
    if seed_line is None:
        raise RuntimeError(f"seed script printed no marker:\n{seeded.stdout[-2000:]}")
    payload = json.loads(seed_line.removeprefix(SEED_MARKER))

    port = _free_port()
    # Uvicorn logs to a file, never a pipe: an unread pipe fills and wedges the
    # server (observed live-suite hangs) — and the file doubles as diagnostics.
    log_path = Path(__file__).resolve().parent / ".live-backend.log"
    log_file = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            shutil.which("uv") or "uv",
            "run",
            "--directory",
            str(BACKEND_DIR),
            "python",
            "-m",
            "uvicorn",
            "config.asgi:application",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        env=_subprocess_env(),
        cwd=str(BACKEND_DIR),
    )
    log_file.close()  # the child owns the handle now (EOF when it exits)
    origin = f"http://127.0.0.1:{port}"
    try:
        _wait_for_health(origin, process, _SERVER_START_TIMEOUT_SECONDS, log_path)
    except BaseException:
        process.terminate()
        raise
    backend = LiveBackend(
        origin=origin,
        project_id=payload["project_id"],
        tasks=tuple(payload["tasks"]),
        tokens=tuple(payload["tokens"]),
        decomposer_token=payload.get("decomposer_token"),
        auditable_task=payload.get("auditable_task"),
        auditor_coder_session=payload.get("auditor_coder_session"),
        process=process,
        log_path=log_path,
    )
    return backend


def stop_live_backend(backend: LiveBackend | None = None) -> None:
    """Terminate the spawned uvicorn (idempotent) and release the log handle."""
    process = backend.process if backend is not None else None
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=15)
