"""Shared entry-point bootstrap and mode dispatch (Sections 10.2, 10.11; MT-2.1-04).

One path for every invocation: parse CLI args, load layered config (MT-2.1-02),
install structured logging (MT-2.1-03), install the correlation scope, resolve
the run mode, dispatch. **Mode selection precedence** (documented in
``bridge/.env.example`` and ``bridge/user-config.example.toml``):

1. explicit invocation — a mode-specific console script (``orchestrator-bridge-stdio``,
   ``orchestrator-bridge-http``, ``orchestrator-bridge-executor``) or ``--mode``
   on the generic entry (``orchestrator-bridge`` / ``python -m orchestrator_bridge``);
2. the configured mode key — ``ORCHESTRATOR_BRIDGE_MODE`` env over the ``mode``
   key of the user config file (MT-2.1-02 layering);
3. default ``stdio``.

Exit codes: ``0`` success, ``1`` startup/configuration error (fail fast,
NFR-10 — layered-config problems and, from WP-2.2, manifest/token binding
failures of Section 10.3 steps 1–3), ``2`` mode not yet implemented (a stub
must never look healthy — MT-2.1-04 risk note).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ..config import ConfigError, RunMode, Settings, load_settings, validate_for_mode
from ..correlation import init_from_env
from ..logging import configure_logging

__all__ = [
    "EXIT_CONFIG_ERROR",
    "EXIT_NOT_IMPLEMENTED",
    "EXIT_OK",
    "cli",
    "cli_entry",
    "resolve_mode",
]

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_NOT_IMPLEMENTED = 2


def resolve_mode(explicit: RunMode | None, settings: Settings) -> RunMode:
    """Explicit invocation > configured key (already layered) > default stdio."""
    return explicit if explicit is not None else settings.mode


def cli(argv: Sequence[str] | None = None, *, explicit_mode: RunMode | None = None) -> int:
    """Parse arguments, load config, configure logging, dispatch the run mode.

    ``argv`` defaults to the process arguments; ``explicit_mode`` is set by the
    mode-specific console scripts and wins over both ``--mode`` and config.
    Configuration problems print one clear line to stderr (no traceback, no
    secret) and return :data:`EXIT_CONFIG_ERROR`.
    """
    parser = argparse.ArgumentParser(
        prog="orchestrator-bridge",
        description="MCP bridge for the AI Agent Task Orchestrator (parent plan Section 10).",
    )
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in RunMode],
        default=None,
        help="run mode; explicit invocation beats ORCHESTRATOR_BRIDGE_MODE, "
        "which beats the default (stdio)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="merge-executor only: process the current queue snapshot once and "
        "exit (the on-demand launch form of Section 10.2)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    explicit = explicit_mode
    if explicit is None and args.mode is not None:
        explicit = RunMode(args.mode)

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    mode = resolve_mode(explicit, settings)
    if args.once and mode is not RunMode.MERGE_EXECUTOR:
        print(
            f"configuration error: --once is only valid for the "
            f"{RunMode.MERGE_EXECUTOR.value} mode (got '{mode.value}')",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR
    configure_logging(settings, mode=mode)
    init_from_env()
    if mode is RunMode.MERGE_EXECUTOR:
        from . import executor

        try:
            # WP-3.7: validate_for_mode requires merge_repo_paths (Section
            # 10.2); resolve_merge_step returns the composed worktree +
            # strategy step (MT-3.7-03/04) — the NotImplementedError
            # backstop below is never hit once those have landed.
            return executor.run(settings, once=args.once)
        except ConfigError as exc:
            print(f"configuration error: {exc}", file=sys.stderr)
            return EXIT_CONFIG_ERROR
        except NotImplementedError as exc:
            print(str(exc), file=sys.stderr)
            return EXIT_NOT_IMPLEMENTED

    validate_for_mode(settings, mode)  # STDIO/HTTP: no required keys today
    if mode is RunMode.HTTP:
        from . import http

        return http.run(settings)
    from . import stdio

    return stdio.run(settings)


def cli_entry() -> int:
    """Zero-argument wrapper for the generic console script (process argv)."""
    return cli()
