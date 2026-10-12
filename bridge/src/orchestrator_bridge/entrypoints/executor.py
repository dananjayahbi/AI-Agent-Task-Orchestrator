"""Merge Executor run mode stub (parent plan Sections 10.1 item 7, 10.2, 11.4; MT-2.1-04).

Host-side executor serving approvals from web/mobile (ADR-008: merge performed
by a host-side Merge Executor). Binding source per Section 10.2: "config
listing allowed repo paths" — ``ORCHESTRATOR_MERGE_REPO_PATHS`` /
``merge_repo_paths`` (validated by ``config.validate_for_mode``). Implemented by
WP-3.7 (Merge queue and Merge Executor). The importable callable raises at the
boundary so an in-process runtime can never mistake "unimplemented" for "done".
"""

from __future__ import annotations

from ..config import RunMode, Settings
from ..logging import get_logger
from . import cli

__all__ = ["NOT_IMPLEMENTED_MESSAGE", "main", "run"]

NOT_IMPLEMENTED_MESSAGE = (
    "Merge Executor run mode is not yet implemented (tracked by WP-3.7 — Merge "
    "queue and Merge Executor); no executor was started."
)


def run(settings: Settings) -> None:
    """Raise at the WP-3.7 boundary; in-process callers catch or propagate."""
    get_logger("executor").warning(
        "run mode requested before implementation",
        extra={"event": "mode_not_implemented", "mode": RunMode.MERGE_EXECUTOR.value},
    )
    raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)


def main() -> int:
    """Console-script entry (``orchestrator-bridge-executor``): explicit executor mode."""
    return cli(explicit_mode=RunMode.MERGE_EXECUTOR)
