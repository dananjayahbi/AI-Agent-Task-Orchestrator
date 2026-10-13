"""STDIO run mode (parent plan Section 10.2; FR-MCP-01; MT-2.1-04, MT-2.2-01…05).

Spawned by the agent CLI inside the repository directory (Claude Code, OpenCode,
Aider and other CLIs); binds the session by working directory. Builds the shared
server (``server.create_server``) and serves MCP over stdin/stdout, with the
bridge's structured diagnostics on **stderr** so they can never corrupt the
JSON-RPC framing (verified against the MCP Python SDK — see the logging module).

Startup order (Section 10.3, WP-2.2 complete): discover the manifest upward to
the Git root, validate it against the published schema and version, prove the
token is configured (steps 1–3), then open the backend agent session and cache
the project context (steps 4–5, MT-2.2-04/05 — including the project-mismatch
abort). A binding failure at any step is logged as ``event=binding_failed``
(correlation id included), printed as one scrubbed stderr line, and exits
:data:`EXIT_CONFIG_ERROR`: the bridge never serves unbound (FR-MCP-02; MT-2.2-01
"no silent fallback").

Teardown (MT-2.2-04): after the clean shutdown (stdin close) the session end
runs best-effort with a bounded timeout — it logs and exits without hanging;
a crashed bridge skips it and the backend's staleness handling covers it.
"""

from __future__ import annotations

import sys

from ..config import RunMode, Settings, validate_for_mode
from ..errors import BindingError
from ..logging import get_logger
from ..manifest import bind_startup
from ..scrub import scrub_text
from ..server import create_server
from ..session import close_session, open_session
from ..submission_spool import SubmissionSpool
from ..tools.runtime import ToolRuntime
from ..transport import ApiClient
from . import EXIT_CONFIG_ERROR, cli

__all__ = ["main", "run"]


def run(settings: Settings) -> int:
    """Run the Section 10.3 startup sequence, serve MCP on stdio, wind down.

    Returns after a clean shutdown (stdin close, session ended best-effort);
    returns :data:`EXIT_CONFIG_ERROR` when binding fails at any of the five
    steps — logged, one scrubbed stderr line, no traceback, no secret.
    """
    validate_for_mode(settings, RunMode.STDIO)
    logger = get_logger("stdio")
    try:
        binding = bind_startup(settings)  # steps 1–3
        client = ApiClient.for_binding(binding, settings)
        session = open_session(binding, settings, client=client, mode=RunMode.STDIO)  # 4–5
    except BindingError as exc:
        logger.error(
            str(exc),
            extra={
                "event": "binding_failed",
                "mode": RunMode.STDIO.value,
                "error_type": type(exc).__name__,
            },
        )
        print(f"bridge startup error: {scrub_text(str(exc))}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    spool = SubmissionSpool.default()
    runtime = ToolRuntime.from_session(binding, client, session, spool=spool)
    # MT-2.6-05 restart recovery: replay this project's unacknowledged
    # submissions (stored payload, stored idempotency key) before serving.
    # Best-effort by contract — the spool never raises and startup never dies
    # because the backend is unreachable; entries simply stay held.
    try:
        report = spool.resume(client, project_id=binding.project_id)
    except Exception as exc:  # pragma: no cover - defensive: resume is non-raising
        logger.error(
            "submission spool resume failed",
            extra={"event": "spool_resume_failed", "error_type": type(exc).__name__},
        )
    else:
        if any(report.as_dict().values()):
            logger.info(
                "submission spool resume sweep finished",
                extra={"event": "spool_resume", **report.as_dict()},
            )
    server = create_server(settings, runtime=runtime)
    logger.info(
        "bridge starting",
        extra={
            "event": "startup",
            "mode": RunMode.STDIO.value,
            "manifest_path": str(binding.manifest_path),
            "project_id": binding.project_id,
            "agent_session_id": session.agent_session_id,
        },
    )
    server.run(transport="stdio")
    logger.info("bridge stopped", extra={"event": "shutdown", "mode": RunMode.STDIO.value})
    close_session(binding, settings, session)  # best-effort, bounded (MT-2.2-04)
    return 0


def main() -> int:
    """Console-script entry (``orchestrator-bridge-stdio``): explicit STDIO."""
    return cli(explicit_mode=RunMode.STDIO)
