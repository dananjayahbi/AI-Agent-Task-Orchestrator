"""MT-6.3-01 — perf-stack lifecycle: clean image, production topology, up/down.

Brings up the Section 16.1 topology (base compose render: postgres,
redis, migrate, backend, worker, beat, web — **prod settings module**,
no dev bind mounts) under its own compose project ``wp63perf`` and free
host ports (8063/3000 are busy on this host; 8063/3063 are used), so it
never touches other sessions' stacks.

Decisions documented for MT-6.3-02's environment section:

* **Image** — built from ``git archive HEAD backend``: the committed
  batch-10 tree (d703319), *not* the working tree, so in-flight changes
  from concurrent agents cannot leak into the measured code. Tagged
  ``orchestrator-backend:wp63perf``.
* **Secrets** — generated per stack and stored in
  ``e2e/perf/.run/stack-secrets.json`` (gitignored): the shared
  ``infra/compose/.env`` ships placeholders that the prod settings module
  refuses (Section 16.2: SECRET_KEY >= 32 non-placeholder chars, strong
  DB password, at least one non-loopback ALLOWED_HOSTS entry).
* **Push** — enabled with wellformed *fixture* FCM credentials for the
  sender-side dispatch probe (zero registered devices => the transport is
  never built; see ``compose.perf.yaml``).

Commands (docs/plan/perf-runbook.md):
  python e2e/perf/stack.py up         # build image, compose up -d --wait
  python e2e/perf/stack.py down [-v]  # stop (-v wipes volumes: full reset)
  python e2e/perf/stack.py status     # compose ps
"""

from __future__ import annotations

import argparse
import io
import json
import os
import secrets as pysecrets
import shutil
import socket
import subprocess
import sys
import tarfile
from pathlib import Path

from perf_common import (
    DEFAULT_API_BASE,
    DEFAULT_COMPOSE_PROJECT,
    RUN_DIR,
    PerfError,
    compose_argv,
)

SECRETS_PATH = RUN_DIR / "stack-secrets.json"
HEAD_SRC = RUN_DIR / "head-src"
IMAGE_TAG = "orchestrator-backend:wp63perf"
WEB_IMAGE = "orchestrator-web:stub"
API_PORT = 8063
WEB_PORT = 3063

# Wellformed fixture service account — passes fcm_credentials_wellformed
# (JSON object, non-empty private_key); never used to contact Google
# because the fixture stack registers zero devices.
_FIXTURE_PEM = (
    "-----BEGIN PRIVATE KEY-----\\n"  # pragma: allowlist secret
    "WP63-FIXTURE-NOT-A-REAL-KEY\\n"
    "-----END PRIVATE KEY-----\\n"
)
FIXTURE_FCM_CREDENTIALS = (
    '{"type":"service_account","project_id":"wp63perf-fixture",'
    f'"private_key":"{_FIXTURE_PEM}",'
    '"client_email":"wp63-fixture@wp63perf-fixture.iam.gserviceaccount.com",'
    '"client_id":"1","token_uri":"https://oauth2.googleapis.com/token"}'
)  # pragma: allowlist secret


def load_or_create_secrets() -> dict[str, str]:
    """Strong prod-valid secrets for this stack (created once, reused)."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    if SECRETS_PATH.exists():
        data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
        if data.get("secret_key") and data.get("database_password"):
            return data
    data = {
        "secret_key": pysecrets.token_urlsafe(48),
        "database_password": pysecrets.token_urlsafe(24),
    }
    SECRETS_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def stack_env() -> dict[str, str]:
    """Shell-environment overrides for one ``compose up`` (env beats .env)."""
    secrets_data = load_or_create_secrets()
    return {
        # Measured code = committed HEAD image, never the working tree.
        "ORCHESTRATOR_IMAGE_BACKEND": IMAGE_TAG,
        "ORCHESTRATOR_IMAGE_WEB": WEB_IMAGE,
        # MT-6.3-03 serving-layer tuning (miss M-1): uvicorn process count
        # for the Section 18 scenario shape (20 concurrent agents). The
        # before/after series (1 → 4 → 8) is in
        # docs/plan/performance-report.md §7.
        "ORCHESTRATOR_BACKEND_WORKERS": "8",
        # Ports: 8000/3000 occupied by unrelated host processes.
        "ORCHESTRATOR_BIND_ADDR": "127.0.0.1",
        "ORCHESTRATOR_PORT_BACKEND": str(API_PORT),
        "ORCHESTRATOR_PORT_WEB": str(WEB_PORT),
        # Section 16.2 prod validation (infra/compose/.env placeholders refused).
        "ORCHESTRATOR_SECRET_KEY": secrets_data["secret_key"],
        "ORCHESTRATOR_DATABASE_PASSWORD": secrets_data["database_password"],
        "ORCHESTRATOR_DATABASE_URL": (
            "postgresql://orchestrator:"
            f"{secrets_data['database_password']}@postgres:5432/orchestrator"
        ),
        "ORCHESTRATOR_ALLOWED_HOSTS": "perf.local,127.0.0.1,localhost",
        "ORCHESTRATOR_DEBUG": "false",
        # Push wiring for the sender-side dispatch probe (MT-6.3-01).
        "ORCHESTRATOR_PUSH_ENABLED": "true",
        "ORCHESTRATOR_FCM_PROJECT_ID": "wp63perf-fixture",
        "ORCHESTRATOR_FCM_CREDENTIALS_JSON": FIXTURE_FCM_CREDENTIALS,
    }


def assert_port_free(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(1.0)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise PerfError(
                f"host port {port} is already in use — pick a different "
                "ORCHESTRATOR_PORT_* or stop the holder before `stack.py up`"
            )


def build_head_image() -> None:
    """Build IMAGE_TAG from a clean ``git archive HEAD backend`` export."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    if HEAD_SRC.exists():
        shutil.rmtree(HEAD_SRC)
    HEAD_SRC.mkdir(parents=True)

    archived = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD", "backend"],
        capture_output=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    if archived.returncode != 0:
        raise PerfError(
            f"git archive HEAD backend failed: {archived.stderr.decode(errors='replace')}"
        )
    with tarfile.open(fileobj=io.BytesIO(archived.stdout)) as tar:
        tar.extractall(HEAD_SRC)  # noqa: S202 — our own git archive, trusted input
    context = HEAD_SRC / "backend"
    if not (context / "Dockerfile").exists():
        raise PerfError(f"exported context has no Dockerfile: {context}")

    print(f"building {IMAGE_TAG} from git archive HEAD ...")
    completed = subprocess.run(
        ["docker", "build", "-t", IMAGE_TAG, str(context)],
        capture_output=True,
    )
    if completed.returncode != 0:
        tail = completed.stderr.decode(errors="replace")[-4000:]
        raise PerfError(f"docker build failed:\n{tail}")
    print(f"image ready: {IMAGE_TAG}")


def cmd_up(_args: argparse.Namespace) -> int:
    assert_port_free(API_PORT)
    assert_port_free(WEB_PORT)
    build_head_image()
    os.environ.update(stack_env())
    print(f"compose up: project={DEFAULT_COMPOSE_PROJECT} api={DEFAULT_API_BASE}")
    completed = subprocess.run(compose_argv("up", "-d", "--wait"))
    if completed.returncode != 0:
        raise PerfError("compose up failed — see output above; `stack.py status` for state")
    print("stack healthy.")
    print("next: python e2e/perf/seed_perf_fixture.py")
    return 0


def cmd_down(args: argparse.Namespace) -> int:
    os.environ.update(stack_env())
    down_args = ["down", "--remove-orphans"]
    if args.volumes:
        down_args.append("-v")
    completed = subprocess.run(compose_argv(*down_args))
    if completed.returncode != 0:
        raise PerfError("compose down failed")
    if args.volumes and HEAD_SRC.exists():
        shutil.rmtree(HEAD_SRC, ignore_errors=True)
    print(f"stack down{' (volumes wiped)' if args.volumes else ''}.")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    os.environ.update(stack_env())
    return subprocess.run(compose_argv("ps")).returncode


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WP-6.3 perf stack lifecycle (MT-6.3-01).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("up", help="build clean HEAD image + compose up -d --wait")
    down = sub.add_parser("down", help="compose down")
    down.add_argument("-v", "--volumes", action="store_true", help="wipe volumes too")
    sub.add_parser("status", help="compose ps")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    handlers = {"up": cmd_up, "down": cmd_down, "status": cmd_status}
    return handlers[args.command](args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PerfError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
