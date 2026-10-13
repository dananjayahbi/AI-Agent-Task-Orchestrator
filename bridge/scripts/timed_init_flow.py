"""Timed end-to-end run of ``orchestrator init`` against the real backend (WP-2.12).

Section 20.4 item 1 proof for WP-2.12's acceptance — "new repo usable via init
in under 2 minutes": starts the real backend through the live-test harness
(``tests/_live_backend.py`` — migrations + seed + uvicorn against the local
``wp16-pg``), then times the *user-facing* command in a fresh Git repository
from a subdirectory, with an isolated user config (never this machine's real
profile) and the seeded agent token from the environment (the headless path
MT-2.12-02 documents). Backend boot time is reported separately — it is not
part of the init flow the acceptance measures.

Usage (from the repository root): ``uv run --directory bridge python
scripts/timed_init_flow.py`` — requires ``docker start wp16-pg`` (and Redis).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BRIDGE_ROOT = REPO_ROOT / "bridge"
sys.path.insert(0, str(BRIDGE_ROOT))  # import tests._live_backend like pytest does

from tests import _live_backend  # noqa: E402


def _run(args: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    # PYTHONUTF8=1 makes the child's stdout/stderr true UTF-8 on Windows
    # (the console codepage would otherwise leak into redirected pipes);
    # errors="replace" keeps one exotic byte from aborting the harness.
    return subprocess.run(
        args,
        cwd=cwd,
        env={**env, "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )


def main() -> int:
    boot_started = time.perf_counter()
    backend = _live_backend.start_live_backend()
    boot_seconds = time.perf_counter() - boot_started
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as scratch:
            work = Path(scratch)
            repo = work / "fresh-repo"
            repo.mkdir()
            _run(["git", "init", "-q"], cwd=repo, env=dict(os.environ))
            subdir = repo / "src" / "app"
            subdir.mkdir(parents=True)

            profile = work / "profile"  # isolated user config — never the real profile
            env = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith("ORCHESTRATOR_")
            }
            env["APPDATA"] = str(profile)
            env["XDG_CONFIG_HOME"] = str(profile)
            env["ORCHESTRATOR_AGENT_TOKEN"] = backend.tokens[0]

            command = [
                sys.executable,
                "-m",
                "orchestrator_bridge.init",
                "init",
                "--project-id",
                backend.project_id,
                "--api",
                backend.api_base_url,
            ]
            started = time.perf_counter()
            result = _run(command, cwd=subdir, env=env)
            elapsed = time.perf_counter() - started

            manifest = repo / "orchestrator.json"
            config = profile / "orchestrator" / "bridge.toml"
            print(f"backend boot (not counted): {boot_seconds:.1f}s")
            print(f"orchestrator init wall time: {elapsed:.2f}s")
            print(f"exit code: {result.returncode}")
            print(f"manifest at repo root: {manifest.is_file()}")
            print(f"user config written: {config.is_file()}")
            print("--- stdout ---")
            print(result.stdout)
            print("--- stderr (last 15 lines) ---")
            print("\n".join(result.stderr.splitlines()[-15:]))
            ok = (
                result.returncode == 0
                and manifest.is_file()
                and config.is_file()
                and "self-test: all checks passed" in result.stdout
                and "mcpServers" in result.stdout
                and backend.tokens[0] not in result.stdout + result.stderr
            )
            print(f"RESULT: {'PASS' if ok else 'FAIL'} (under 2 minutes: {elapsed < 120})")
            return 0 if ok else 1
    finally:
        _live_backend.stop_live_backend(backend)


if __name__ == "__main__":
    sys.exit(main())
