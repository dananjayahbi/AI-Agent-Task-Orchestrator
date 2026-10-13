"""The ``orchestrator init`` command line (FR-MCP-08; Section 10.11; MT-2.12-01..04).

One subcommand surface for the init duties, matching the plan's ``orchestrator``
CLI name (Section 10.11 "packaging"; full CLI packaging is a later WP — the
module entry ``python -m orchestrator_bridge.init`` runs the same code):

* ``orchestrator init`` — the four duties in FR-MCP-08 order: manifest write,
  token storage, connectivity self-test, then (only on a passing self-test)
  the per-client registration snippets.
* ``orchestrator init --self-test`` — duty 3 standalone, for re-verification
  (the snippets and agent guides point at it); read-only.

Failure posture mirrors the run-mode entry points (NFR-10): configuration or
init problems print **one** scrubbed line to stderr — no traceback, no secret
— and exit non-zero; stdout stays reserved for the flow's own output
(verdicts, snippets). Exit codes: ``0`` success, ``1`` any init/self-test
failure (so scripts and agent guides can gate on it).

Interactive minimum for the "under 2 minutes" acceptance: ``--project-id``
and an environment token make the whole flow non-interactive; without them
init prompts twice — project id (plain) and token (hidden) — and nothing
else. Test seams: ``run_init`` takes ``cwd``, ``prompt`` (project id),
``token_prompt`` (hidden token) and the transport ``send`` seam.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

from ..config import ConfigError, RunMode, load_settings
from ..correlation import init_from_env
from ..errors import BindingError, InitError
from ..logging import configure_logging
from ..manifest_discovery import MANIFEST_FILENAME
from ..transport import ApiClient, SendFn
from .manifest_write import (
    PID_PATTERN,
    WriteOutcome,
    compose_manifest,
    fetch_project_inputs,
    find_git_root,
    write_manifest,
)
from .selftest import CheckResult, all_passed, run_self_test
from .snippets import render_snippets
from .token_store import acquire_token, store_agent_token

__all__ = ["EXIT_FAILURE", "EXIT_OK", "build_parser", "main", "run_init"]

EXIT_OK = 0
EXIT_FAILURE = 1


def build_parser() -> argparse.ArgumentParser:
    """The ``orchestrator`` surface: one ``init`` subcommand today."""
    parser = argparse.ArgumentParser(
        prog="orchestrator",
        description=("AI Agent Task Orchestrator client CLI (parent plan Section 10.11)."),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser(
        "init",
        help=(
            "bootstrap orchestrator.json, store the agent token in user-level "
            "config, and run the connectivity self-test (FR-MCP-08)"
        ),
    )
    init_parser.add_argument(
        "--project-id",
        metavar="PIDxxxxx",
        default=None,
        help="project to bind, verified against the backend; prompted when omitted",
    )
    init_parser.add_argument(
        "--api",
        metavar="URL",
        default=None,
        help="backend API base URL for this run (overrides config/env)",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing orchestrator.json without confirmation",
    )
    init_parser.add_argument(
        "--self-test",
        action="store_true",
        help="run only the connectivity self-test (no writes; re-verification)",
    )
    return parser


def _stdin_prompt(question: str) -> str:
    """Plain prompt for non-secret input (the project id); TTY required."""
    if not sys.stdin.isatty():
        raise InitError(
            "non-interactive run is missing a value that has no flag: pass "
            "--project-id PIDxxxxx (see --help)"
        )
    try:
        return input(question)
    except (EOFError, KeyboardInterrupt):
        raise InitError("prompt cancelled; re-run with --project-id to skip prompts") from None


def _confirm_replace(question: str) -> bool:
    """Overwrite confirmation: non-TTY and cancelled runs decline (→ --force)."""
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(f"{question} [y/N] ")
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().lower() in {"y", "yes"}


def _report(results: tuple[CheckResult, ...]) -> None:
    """Print the per-check verdict lines (NFR-10: one screen, remedy named)."""
    for result in results:
        print(f"self-test [{result.name}] {result.status.upper():4}  {result.detail}")
        if result.remedy is not None:
            print(f"    fix: {result.remedy}")
    if all_passed(results):
        print("self-test: all checks passed")
    else:
        print("self-test: FAILED — apply the fix lines above and re-run")


def _configure_logging_best_effort() -> None:
    """Structured logs when config loads; verdicts must flow even if it cannot."""
    try:
        settings = load_settings()
    except ConfigError:
        return
    configure_logging(settings, mode=RunMode.STDIO)
    init_from_env()


def _command_self_test() -> int:
    _configure_logging_best_effort()
    results = run_self_test()
    _report(results)
    return EXIT_OK if all_passed(results) else EXIT_FAILURE


def run_init(
    args: argparse.Namespace,
    *,
    cwd: Path | None = None,
    prompt: Callable[[str], str] | None = None,
    token_prompt: Callable[[str], str] | None = None,
    send: SendFn | None = None,
) -> int:
    """Execute ``orchestrator init``'s four duties (FR-MCP-08 order).

    Duties 1–2 are mandatory writes; duty 3 gates duty 4 (snippets print only
    on an all-pass self-test — the safe ordering, MT-2.12-04 risk note).
    Returns the process exit code; fatal duty errors raise
    :class:`InitError`/:class:`ConfigError` for :func:`main` to render as one
    scrubbed stderr line.
    """
    start = Path.cwd() if cwd is None else cwd
    ask = _stdin_prompt if prompt is None else prompt

    root = find_git_root(start)
    settings = load_settings()  # env + user config + defaults (MT-2.1-02)
    api_base = args.api if args.api else settings.api_base_url
    if not api_base.startswith(("http://", "https://")):
        raise InitError(
            f"API base URL {api_base!r} must be an http(s):// address; fix "
            "--api or ORCHESTRATOR_API_BASE_URL and re-run"
        )

    # Duty 2's *input* comes first (the token authorizes duty 1's verification
    # reads); the *storage* still lands in duty order below.
    token = acquire_token(prompt=token_prompt)
    settings = replace(settings, agent_token=token, api_base_url=api_base)
    configure_logging(settings, mode=RunMode.STDIO)
    init_from_env()

    project_id = args.project_id or ask("Project ID (PIDxxxxx, from the orchestrator UI): ").strip()
    if not PID_PATTERN.match(project_id):
        raise InitError(
            f"{project_id!r} is not a project id — expected PID followed by "
            "five digits (Section 7.3), e.g. --project-id PID00007"
        )

    # Duty 1 — manifest write, backend-verified (Section 19.3).
    client = ApiClient(settings, base_url=api_base, send=send)
    inputs = fetch_project_inputs(client, project_id)
    document = compose_manifest(inputs, orchestrator_api=api_base)
    manifest_path = root / MANIFEST_FILENAME
    outcome = write_manifest(root, document, force=args.force, confirm=_confirm_replace)
    if outcome is WriteOutcome.UNCHANGED:
        print(f"manifest unchanged: {manifest_path}")
    else:
        print(f"manifest written: {manifest_path} (project {project_id})")

    # Duty 2 — token storage, outside the repository (FR-SEC-04).
    config_path = store_agent_token(token, repo_root=root)
    print(f"agent token stored: {config_path} (value never displayed)")

    # Duty 3 — connectivity self-test (non-zero exit on any failed check).
    results = run_self_test(cwd=start, send=send)
    _report(results)
    if not all_passed(results):
        return EXIT_FAILURE

    # Duty 4 — per-client snippets, only after proven binding (safe ordering).
    print()
    print(render_snippets(config_path=config_path))
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Console/module entry: parse, dispatch, render failures as one line."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.self_test:
            return _command_self_test()
        return run_init(args)
    except (InitError, ConfigError, BindingError, KeyboardInterrupt) as exc:
        message = "cancelled" if isinstance(exc, KeyboardInterrupt) else str(exc)
        print(f"orchestrator init failed: {message}", file=sys.stderr)
        return EXIT_FAILURE
