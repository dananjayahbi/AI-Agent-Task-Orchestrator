"""Runner orchestration and the standalone CLI (MT-2.11-01; Sections 10.8, 18).

Invocation shape (the risk-note decision): a **standalone module entry point**,
not a pytest session. The runner is an agent-facing instrument - it must run
against a live bridge stack outside the test suite, with its own flags, and
exit 0/1 like any conformance tool:

    uv run --directory bridge python -m tests.conformance.runner \
        --manifest /path/to/repo/orchestrator.json \
        --repo /path/to/repo \
        --project-id PID00007 \
        --coder-token $TOKEN --auditor-token $TOKEN --decomposer-token $TOKEN \
        --report conformance-report.json

pytest self-tests call :func:`run_conformance` directly with injected
connections or the stdio transport against the loopback stub
(``tests/test_conformance_harness.py``), so CI proves the instrument works
without a client or a full stack.
"""

from __future__ import annotations

import argparse
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES

from .checks import (
    check_error_catalog,
    check_initialize_rules,
    check_prompt_render,
    check_prompts,
    check_tool_catalog,
)
from .connection import (
    HttpMcpConnection,
    McpConnection,
    StdioMcpConnection,
    default_bridge_command,
    stdio_bridge_env,
)
from .report import CheckResult, ConformanceReport
from .scenarios import (
    CoderOutcome,
    PreparedCommit,
    RoleSession,
    run_auditor_scenario,
    run_coder_scenario,
    run_decomposer_scenario,
)

__all__ = ["RunnerConfig", "main", "prepare_commit", "run_conformance"]

#: Relative path of the marker file the repo-preparation commit writes.
MARKER_PATH = Path("conformance") / "marker.txt"


@dataclass
class RunnerConfig:
    """Everything one conformance run needs; the CLI maps flags onto this."""

    manifest_path: Path | None = None
    repo_path: Path | None = None
    report_path: Path | None = None
    project_id: str = "PID00007"
    transport: str = "stdio"  # "stdio" or "http"
    http_base_url: str | None = None
    coder_token: str = ""
    auditor_token: str = ""
    decomposer_token: str = ""
    spool_dir: Path | None = None
    capability: str | None = None  # "vision" | "text_only" | None (unknown)
    client_label: str = "Custom agent (conformance runner)"
    expected_project_rules: str | None = None
    coder_task_id: str | None = None
    command: list[str] = field(default_factory=default_bridge_command)
    cwd: Path | None = None


def _run_git(repo: Path, *args: str) -> str:
    """One git invocation in *repo*; non-zero exit raises with stderr attached."""
    completed = subprocess.run(  # noqa: S603 - list args, shell=False
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def prepare_commit(repo: Path, branch: str) -> PreparedCommit:
    """Ensure *branch* exists in *repo* with one fresh commit; return its tip.

    The submit tool verifies branch name, reachable sha and a clean working
    tree (WP-2.10 ``verify_submission``), so this preparation:

    1. requires an existing git work tree (fail loudly otherwise);
    2. gives the repo a local identity only when none is configured, so the
       marker commit never depends on the operator's global git config;
    3. creates or resets the branch at the current HEAD, writes the marker
       file and commits it (``--allow-empty`` keeps reruns deterministic).
    """
    _run_git(repo, "rev-parse", "--git-dir")
    try:
        _run_git(repo, "rev-parse", "--verify", "HEAD")
    except RuntimeError:
        _ensure_identity(repo)
        _run_git(repo, "commit", "--allow-empty", "-m", "conformance: initial commit")
    _ensure_identity(repo)
    _run_git(repo, "checkout", "-B", branch)
    marker = repo / MARKER_PATH
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(f"conformance marker (MT-2.11-01) at {time.time():.3f}\n", encoding="utf-8")
    _run_git(repo, "add", "-A")
    _run_git(repo, "commit", "--allow-empty", "-m", "conformance: compatibility run marker")
    return PreparedCommit(branch=branch, sha=_run_git(repo, "rev-parse", "HEAD"))


def _ensure_identity(repo: Path) -> None:
    """Local (never global) identity so commits work on a bare CI machine."""
    for key, value in (
        ("user.email", "conformance@orchestrator.invalid"),
        ("user.name", "Conformance Runner"),
    ):
        try:
            _run_git(repo, "config", key)
        except RuntimeError:
            _run_git(repo, "config", key, value)


def _default_spool(config: RunnerConfig) -> Path:
    """A spool directory outside the submission repo (never the user profile)."""
    if config.spool_dir is not None:
        return config.spool_dir
    if config.repo_path is not None:
        return config.repo_path.parent / ".conformance-spool"
    if config.manifest_path is not None:
        return config.manifest_path.parent / ".conformance-spool"
    raise ValueError("a stdio run needs --manifest or --repo (spool directory)")


def run_conformance(config: RunnerConfig) -> ConformanceReport:
    """Drive one full run: coder, auditor and decomposer sessions, in order."""
    report = ConformanceReport(client_label=config.client_label, transport=config.transport)
    spool_dir = _default_spool(config)

    def connect(role: str, token: str) -> McpConnection:
        if config.transport == "http":
            if config.http_base_url is None:
                raise ValueError("an http run needs --base-url")
            return HttpMcpConnection(config.http_base_url, config.project_id, token)
        if config.manifest_path is None:
            raise ValueError("a stdio run needs --manifest")
        env = stdio_bridge_env(
            manifest_path=config.manifest_path,
            token=token,
            spool_dir=spool_dir,
            session_capability=config.capability,
        )
        connection = StdioMcpConnection(list(config.command), env=env, cwd=config.cwd)
        connection.open()
        return connection

    outcome = CoderOutcome()
    try:
        outcome = _run_coder(config, report, connect)
        _run_auditor(config, report, connect, outcome)
        _run_decomposer(config, report, connect)
    finally:
        _record_coverage(config, report)
    return report


def _run_coder(
    config: RunnerConfig,
    report: ConformanceReport,
    connect: Callable[[str, str], McpConnection],
) -> CoderOutcome:
    outcome = CoderOutcome()
    try:
        connection = connect("coder", config.coder_token)
    except Exception as exc:  # noqa: BLE001 - a dead transport is a finding, not a crash
        report.add(CheckResult("connect.coder", "coder", "fail", f"connect failed: {exc}"))
        return outcome
    try:
        init = connection.initialize()
        report.protocol_version = str(init.get("protocolVersion") or "")
        info = init.get("serverInfo")
        if isinstance(info, dict):
            report.bridge_version = f"{info.get('name', '')} {info.get('version', '')}".strip()
        check_initialize_rules(report, init.get("instructions"))
        check_tool_catalog(report, "coder", connection.list_tools())
        surfaced = check_prompts(report, connection.list_prompts())
        for name in surfaced:
            try:
                check_prompt_render(report, name, connection.get_prompt(name))
            except Exception as exc:  # noqa: BLE001 - render failure is a finding
                check_prompt_render(report, name, None, error=str(exc))
        session = RoleSession(report, connection, "coder")
        prepare: Callable[[str], PreparedCommit] | None = None
        if config.repo_path is not None:
            prepare = partial(prepare_commit, config.repo_path)
        outcome = run_coder_scenario(
            report,
            session,
            capability=config.capability,
            project_id=config.project_id,
            prepare_commit=prepare,
            expected_project_rules=config.expected_project_rules,
            prefer_task_id=config.coder_task_id,
        )
    except Exception as exc:  # noqa: BLE001 - any session crash is a failed check
        report.add(CheckResult("connect.coder", "coder", "fail", f"coder scenario crashed: {exc}"))
    finally:
        connection.close()
    return outcome


def _run_auditor(
    config: RunnerConfig,
    report: ConformanceReport,
    connect: Callable[[str, str], McpConnection],
    outcome: CoderOutcome,
) -> None:
    try:
        connection = connect("auditor", config.auditor_token)
    except Exception as exc:  # noqa: BLE001 - a dead transport is a finding
        report.add(CheckResult("connect.auditor", "auditor", "fail", f"connect failed: {exc}"))
        return
    try:
        connection.initialize()
        run_auditor_scenario(
            report,
            RoleSession(report, connection, "auditor"),
            prefer_task_id=outcome.submitted_task_id,
            expected_project_rules=config.expected_project_rules,
        )
    except Exception as exc:  # noqa: BLE001 - any session crash is a failed check
        report.add(
            CheckResult("connect.auditor", "auditor", "fail", f"auditor scenario crashed: {exc}")
        )
    finally:
        connection.close()


def _run_decomposer(
    config: RunnerConfig,
    report: ConformanceReport,
    connect: Callable[[str, str], McpConnection],
) -> None:
    try:
        connection = connect("decomposer", config.decomposer_token)
    except Exception as exc:  # noqa: BLE001 - a dead transport is a finding
        report.add(
            CheckResult("connect.decomposer", "decomposer", "fail", f"connect failed: {exc}")
        )
        return
    try:
        connection.initialize()
        run_decomposer_scenario(report, RoleSession(report, connection, "decomposer"))
    except Exception as exc:  # noqa: BLE001 - any session crash is a failed check
        report.add(
            CheckResult(
                "connect.decomposer", "decomposer", "fail", f"decomposer scenario crashed: {exc}"
            )
        )
    finally:
        connection.close()


def _record_coverage(config: RunnerConfig, report: ConformanceReport) -> None:
    """The Section 10.5 coverage assertion plus the catalog-membership check."""
    expected = set(CORE_TOOL_NAMES)
    if config.repo_path is None:
        expected.discard("submit_task_resolution")
    if report.attachment_skipped:
        expected.discard("read_task_attachment")
    missing = sorted(expected - set(report.tools_exercised))
    if missing:
        report.add(
            CheckResult(
                "catalog.tools_exercised",
                "all",
                "fail",
                f"tools never exercised this run: {missing}",
            )
        )
    else:
        report.add(
            CheckResult(
                "catalog.tools_exercised",
                "all",
                "pass",
                f"all {len(expected)} applicable Section 10.5 tools exercised",
            )
        )
    check_error_catalog(report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tests.conformance.runner",
        description=(
            "MCP client-compatibility conformance runner (MT-2.11-01). Drives "
            "the Section 10.5 catalog as coder/auditor/decomposer and writes "
            "the Section 10.9 matrix row plus per-check evidence."
        ),
    )
    parser.add_argument(
        "--manifest", type=Path, help="orchestrator.json of the bridge to drive (stdio)"
    )
    parser.add_argument("--repo", type=Path, help="git repo for the submit step (optional)")
    parser.add_argument("--report", type=Path, help="where to write the JSON report")
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    parser.add_argument("--base-url", help="running bridge base URL (http transport)")
    parser.add_argument("--project-id", default="PID00007")
    parser.add_argument("--coder-token", default="")
    parser.add_argument("--auditor-token", default="")
    parser.add_argument("--decomposer-token", default="")
    parser.add_argument(
        "--capability",
        choices=("vision", "text_only"),
        default=None,
        help="session capability announced to the bridge (default: unknown = text-safe)",
    )
    parser.add_argument("--client-label", default="Custom agent (conformance runner)")
    parser.add_argument(
        "--expected-project-rules",
        help="substring the project rules must contain in delivered rules blocks",
    )
    parser.add_argument(
        "--coder-task",
        help="prefer this pending task id for the coder claim (live seeded runs)",
    )
    parser.add_argument("--cwd", type=Path, help="working directory for the spawned bridge")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = RunnerConfig(
        manifest_path=args.manifest,
        repo_path=args.repo,
        report_path=args.report,
        project_id=args.project_id,
        transport=args.transport,
        http_base_url=args.base_url,
        coder_token=args.coder_token,
        auditor_token=args.auditor_token,
        decomposer_token=args.decomposer_token,
        capability=args.capability,
        client_label=args.client_label,
        expected_project_rules=args.expected_project_rules,
        coder_task_id=args.coder_task,
        cwd=args.cwd,
    )
    report = run_conformance(config)
    if args.report is not None:
        report.write(args.report)
    print(report.summary())
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover - exercised by the live run
    raise SystemExit(main())
