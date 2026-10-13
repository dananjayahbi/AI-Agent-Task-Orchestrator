"""Local HTTP service for the MCP bridge (parent plan Section 10.2; WP-2.9).

One long-running local process serving MCP over HTTP with SSE for
server-to-client messages (FR-MCP-01: one codebase, two transports — the
stdio path of :mod:`orchestrator_bridge.entrypoints.stdio` shares the same
``server.create_server`` registry). Each connection binds to a project from
its URL path plus a project-scoped token (Section 10.2 run-modes table);
the two-connections isolation guarantee is WP-2.9's acceptance.

Module map:

* :mod:`responses` — Section 9.2 error envelopes and JSON replies.
* :mod:`binding` — URL/token validation and the per-connection session open.
* :mod:`connection` — one connection's state machine and teardown.
* :mod:`registry` — admission, lookup, idle sweep, shutdown close-out.
* :mod:`app` — the ASGI application (``/health`` + the MCP endpoint).
* :mod:`runner` — uvicorn construction and the run-mode entry behaviour.
"""

from __future__ import annotations

from .app import HttpBridgeApp, create_http_app
from .registry import ConnectionRegistry

__all__ = ["ConnectionRegistry", "HttpBridgeApp", "create_http_app"]
