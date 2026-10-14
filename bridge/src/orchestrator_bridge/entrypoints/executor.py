"""Merge Executor run mode (parent plan Sections 10.1 item 7, 10.2, 11.4; WP-3.7).

Host-side executor serving approvals from web/mobile (ADR-008: the merge
is performed by a host-side Merge Executor, never by the backend —
Principle P2 / ADR-007). Binding source per Section 10.2: "config
listing allowed repo paths" — ``ORCHESTRATOR_MERGE_REPO_PATHS`` /
``merge_repo_paths`` (validated by ``config.validate_for_mode``).

MT-3.7-02 wires the Section 11.4 loop from :mod:`orchestrator_bridge
.merge_executor`: poll ``GET /merge/pending`` → claim ``POST
/merge/{task}/start`` → merge step (MT-3.7-03's isolated temp worktree
plus MT-3.7-04's strategies) → report ``POST /merge/{task}/result``.
The step itself is resolved once at startup by
:func:`~orchestrator_bridge.merge_executor.resolve_merge_step`, which
composes MT-3.7-03's isolated temp worktree with MT-3.7-04's strategies,
so this mode never claims a task it cannot finish.

Launch forms (Section 10.2): long-running host process (default) or
on-demand command (``--once`` — one queue pass, then exit).

Exit codes: ``0`` clean shutdown (including Ctrl-C on the long-running
form); ``1`` configuration problem (missing allowlist or agent token)
or unrecoverable runtime stop (a merge report that stayed unconfirmed
after backoff — MT-3.7-06 reconciles it on the next start; a
non-retryable backend error such as a revoked token).
"""

from __future__ import annotations

import sys

from ..api_errors import ApiError
from ..config import RunMode, Settings, validate_for_mode
from ..errors import BindingError
from ..logging import get_logger
from ..merge_executor import (
    MergeExecutorLoop,
    MergeQueueClient,
    MergeRecoveryError,
    MergeReportError,
    resolve_merge_step,
    startup_recovery,
)
from ..transport import ApiClient
from . import EXIT_CONFIG_ERROR, EXIT_OK, cli

__all__ = ["main", "run"]


def run(settings: Settings, *, once: bool = False) -> int:
    """Validate, wire the loop, and serve the merge queue (Section 11.4).

    ``once`` is the on-demand launch form: process the current queue
    snapshot and exit (Section 10.2's two launch forms share this entry).

    Raises :class:`~orchestrator_bridge.config.ConfigError` when the
    allowlist is unset — in-process callers fail fast instead of
    mistaking a misconfigured run for a healthy one.
    """
    validate_for_mode(settings, RunMode.MERGE_EXECUTOR)
    # Boundary first: never build a loop (or touch the API) that could
    # claim tasks the current build has no step to finish.
    merge_step = resolve_merge_step(settings)
    log = get_logger("executor")
    try:
        api = ApiClient(settings)
    except BindingError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    queue = MergeQueueClient(api)
    try:
        # Single-worker lock held for the whole run + leftover cleanup +
        # journal reconciliation (MT-3.7-06) — before the first claim.
        _lock, journal = startup_recovery(settings, queue)
    except MergeRecoveryError as exc:
        log.error(str(exc), extra={"event": "merge_startup_recovery_failed"})
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG_ERROR
    loop = MergeExecutorLoop(settings, queue, merge_step, journal=journal)
    try:
        if once:
            handled = loop.run_once()
            log.info(
                "merge queue pass complete",
                extra={"event": "executor_pass_complete", "handled": handled},
            )
        else:
            loop.run_forever()
    except KeyboardInterrupt:
        log.info("merge executor interrupted", extra={"event": "executor_interrupted"})
        return EXIT_OK
    except MergeReportError as exc:
        # Loud, designed stop: the report's idempotency key was logged by
        # the loop; MT-3.7-06's reconciliation is the recovery path.
        log.error(str(exc), extra={"event": "executor_stopped_unconfirmed"})
        return EXIT_CONFIG_ERROR
    except ApiError as exc:
        log.error(
            "merge executor stopped by a non-retryable backend error",
            extra={"event": "executor_stopped", "error_code": str(exc.code)},
        )
        return EXIT_CONFIG_ERROR
    return EXIT_OK


def main() -> int:
    """Console-script entry (``orchestrator-bridge-executor``): explicit executor mode."""
    return cli(explicit_mode=RunMode.MERGE_EXECUTOR)
