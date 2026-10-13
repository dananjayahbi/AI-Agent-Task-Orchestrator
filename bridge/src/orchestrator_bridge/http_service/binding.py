"""Per-connection binding: URL project id + project-scoped token (Sections 10.2,
10.3 step 4, FR-MCP-06; MT-2.9-02).

The HTTP/SSE run mode's binding source is *per-connection* — "project id in URL
path plus project-scoped token" (Section 10.2) — unlike stdio's working
directory. This module owns the first barrier:

* the URL project id is validated against the manifest schema's canonical
  pattern (``^PID[0-9]{5}$``) **before any backend call** — a malformed id is a
  connection-level ``VALIDATION_ERROR`` and never reaches the filesystem (a
  path-derived id must not drive a manifest lookup; HTTP mode has no manifest
  at all — MT-2.9-02 risk note);
* the presented ``Authorization: Bearer`` token must be present and
  header-safe (the stdio step-3 rule, :func:`header_safe`);
* the backend session opens with **that token** (ADR-004: the body carries no
  project — the backend resolves and verifies the token's project) and the
  project context is read for the *URL's* project, so a token scoped to
  another project fails here with ``AUTH_FORBIDDEN_PROJECT`` and **no session
  state survives** (FR-MCP-06 second barrier; Section 10.3 step 4 semantics —
  mismatch aborts this connection).

A connection's binding is a synthetic :class:`StartupBinding`: manifest fields
the tools need but that no manifest supplies over HTTP are present only where
the plan documents a default (G-09's ``feat/{PID}-`` branch prefix). The
backend address comes from the layered configuration (Section 9.10), never
from the URL.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final

from ..api_errors import ApiError, ErrorCode
from ..config import Settings
from ..credentials import header_safe
from ..endpoints import endpoint
from ..logging import get_logger
from ..manifest import StartupBinding
from ..scrub import scrub_text
from ..session import (
    CAPABILITY_UNKNOWN,
    CLIENT_NAME,
    AgentSession,
    fetch_project_context,
    new_session_id,
)
from ..transport import ApiClient, SendFn

__all__ = [
    "ConnectionRejection",
    "OpenedConnection",
    "PROJECT_ID_PATTERN",
    "bearer_token_from_headers",
    "open_connection",
    "parse_project_id",
    "synthetic_binding",
]

#: The manifest schema's canonical project id (schemas/manifest.v1.json).
PROJECT_ID_PATTERN: Final = re.compile(r"\APID[0-9]{5}\Z")

#: Pseudo-path for a connection that has no manifest on disk (HTTP mode binds
#: from the URL, Section 10.2) — never opened, never created.
HTTP_BINDING_PATH: Final = Path("(per-connection)")

_LOGGER_COMPONENT = "http.binding"


class ConnectionRejection(Exception):
    """A connection refused before it exists: HTTP status + Section 9.2 code.

    Carries the exact envelope fields the caller writes; ``details`` holds the
    Section 10.5 hint/next-action pair (error-envelope.md rule 5 keeps them off
    the top level). Never carries token bytes.
    """

    def __init__(
        self,
        status: int,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = dict(details) if details is not None else None


@dataclass(frozen=True, slots=True)
class OpenedConnection:
    """The three Section 10.3 step 4-5 products for one connection."""

    binding: StartupBinding
    client: ApiClient
    session: AgentSession


def parse_project_id(raw: str) -> str:
    """Validate the URL-derived project id before anything else sees it.

    Raises :class:`ConnectionRejection` (400 ``VALIDATION_ERROR``) for any
    value outside the canonical pattern — the URL is attacker-controllable
    input (MT-2.9-02 risk note), so it is checked, not sanitized.
    """
    if not PROJECT_ID_PATTERN.match(raw):
        raise ConnectionRejection(
            400,
            ErrorCode.VALIDATION_ERROR,
            f"invalid project id {raw!r} in the connection URL.",
            details={
                "hint": "the project id in the URL path must match ^PID[0-9]{5}$.",
                "next_action": "Connect to /projects/<canonical project id>/mcp "
                "using the id shown in the owner's project page.",
                "reason": "invalid_project_id",
            },
        )
    return raw


def bearer_token_from_headers(headers: list[tuple[bytes, bytes]]) -> str:
    """Extract and gate the per-connection bearer token from ASGI headers.

    Missing header, a non-Bearer scheme, an empty value or an unsafe value
    (whitespace/control characters — the stdio ``header_safe`` rule) all raise
    ``AUTH_REQUIRED`` with a fix-oriented hint; the message never echoes the
    presented value.
    """
    raw: str | None = None
    for name, value in headers:
        if name.lower() == b"authorization":
            raw = value.decode("latin-1")
            break
    if raw is None:
        raise _auth_required("no Authorization header on the connection request.")
    scheme, separator, token = raw.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise _auth_required("the Authorization header must carry a Bearer token.")
    token = token.strip()
    if not header_safe(token):
        raise _auth_required("the presented bearer token is not a valid credential value.")
    return token


def _auth_required(message: str) -> ConnectionRejection:
    return ConnectionRejection(
        401,
        ErrorCode.AUTH_REQUIRED,
        message,
        details={
            "hint": "HTTP/SSE connections authenticate per request with a "
            "project-scoped agent token (Section 10.2).",
            "next_action": "Add 'Authorization: Bearer <token>' from the "
            "owner-issued project token (or run 'orchestrator init') and reconnect.",
        },
    )


def synthetic_binding(project_id: str) -> StartupBinding:
    """The HTTP-mode binding: URL project id, no manifest on disk.

    ``auto_branch_prefix`` carries G-09's documented default (``feat/{PID}-``)
    because the key's fallback rule is part of the branch contract
    (MT-2.10-02) and ``claim_task`` reads it from the binding; every other
    manifest field is intentionally absent — the backend owns the rest
    (Section 19.3: nothing derived client-side).
    """
    return StartupBinding(
        manifest_path=HTTP_BINDING_PATH,
        manifest={
            "project_id": project_id,
            "auto_branch_prefix": f"feat/{project_id}-",
        },
    )


def connection_settings(settings: Settings, token: str) -> Settings:
    """Layer the presented token into this connection's settings copy.

    The token lives only inside the returned frozen ``Settings`` (the single
    redaction boundary, MT-2.1-02/03); it is never stored elsewhere.
    """
    return replace(settings, agent_token=token)


def open_connection(
    project_id: str,
    token: str,
    settings: Settings,
    *,
    send: SendFn | None = None,
) -> OpenedConnection:
    """Open the backend session for one connection (Section 10.3 steps 4-5).

    Composed from the session layer's primitives rather than
    :func:`session.open_session` because HTTP needs two things stdio does not:
    the raw ``ApiError`` code for per-connection status mapping, and a
    best-effort ``POST /agent-sessions/{id}/end`` when step 5 fails *after*
    the session was created — "reject the connection with no session state"
    (MT-2.9-02). Backend rejections surface as :class:`ConnectionRejection`.
    """
    binding = synthetic_binding(project_id)
    conn_settings = connection_settings(settings, token)
    client = ApiClient.for_binding(binding, conn_settings, send=send)
    session_id = new_session_id()
    payload = {
        "id": session_id,
        "client_name": CLIENT_NAME,
        "capability": CAPABILITY_UNKNOWN,
        # Section 10.2 run mode -> the backend's TransportEnum value "http".
        "transport": "http",
    }
    logger = get_logger(_LOGGER_COMPONENT)
    try:
        response = client.request("POST", endpoint("session_open").path, body=payload)
    except ApiError as exc:
        raise rejection_for(project_id, exc) from None
    agent_session_id = (
        str(response.get("id"))
        if isinstance(response, Mapping) and isinstance(response.get("id"), str)
        else session_id
    )
    try:
        context = fetch_project_context(client, binding)
    except ApiError as exc:
        _end_quietly(client, project_id, agent_session_id)
        raise rejection_for(project_id, exc) from None
    logger.info(
        "agent session opened",
        extra={
            "event": "session_opened",
            "agent_session_id": agent_session_id,
            "project_id": project_id,
            "transport": "http",
        },
    )
    return OpenedConnection(
        binding=binding,
        client=client,
        session=AgentSession(agent_session_id=agent_session_id, context=context),
    )


def rejection_for(project_id: str, error: ApiError) -> ConnectionRejection:
    """Map a backend failure to the connection's Section 9.2 rejection.

    ``AUTH_FORBIDDEN_PROJECT`` (403) is the token-for-another-project case —
    the backend's verification is the authority (FR-SEC-01) and this
    connection gets the same remedy-bearing vocabulary as stdio's
    project-mismatch abort. ``AUTH_REQUIRED`` (401) is an unrecognised or
    revoked credential; anything else is ``SERVER_ERROR``, retryable exactly
    as the backend flagged it (Section 10.10).
    """
    message = scrub_text(error.message)
    if error.code is ErrorCode.AUTH_FORBIDDEN_PROJECT:
        return ConnectionRejection(
            403,
            ErrorCode.AUTH_FORBIDDEN_PROJECT,
            f"The presented agent token is not valid for project {project_id} (backend: {message})",
            details={
                "hint": "one agent token is scoped to exactly one project "
                "(Section 10.3); a connection may only bind its token's project.",
                "next_action": f"Present the project-scoped token issued for "
                f"{project_id}, or connect to the URL of the project the "
                f"presented token belongs to.",
                "project_id": project_id,
            },
        )
    if error.code is ErrorCode.AUTH_REQUIRED:
        return ConnectionRejection(
            401,
            ErrorCode.AUTH_REQUIRED,
            f"The presented agent token was rejected by the backend ({message})",
            details={
                "hint": "tokens are issued per project by the owner and can be "
                "revoked; rejected values never work again.",
                "next_action": "Request a fresh project token from the owner "
                "(or run 'orchestrator init') and reconnect.",
            },
        )
    return ConnectionRejection(
        503 if error.retryable else 500,
        ErrorCode.SERVER_ERROR,
        f"Could not open a session for project {project_id} (backend: {message})",
        retryable=error.retryable,
        details={
            "hint": "the bridge serves only bound sessions (Section 10.3 "
            "step 4); this failure came from the backend.",
            "next_action": "Retry after the backend is reachable; if it "
            "persists, inspect the backend health.",
            "backend_code": str(error.code),
        },
    )


def _end_quietly(client: ApiClient, project_id: str, agent_session_id: str) -> None:
    """Best-effort session end after a failed step 5 — never raises.

    The session row exists only because the open succeeded; ending it here is
    what keeps a rejected connection from leaving backend state behind
    (MT-2.9-02 "no session state"). Failure degrades to one log line — the
    backend's staleness handling covers it (Section 10.10).
    """
    path = endpoint("session_end").path.format(id=agent_session_id)
    logger = get_logger(_LOGGER_COMPONENT)
    try:
        client.request("POST", path)
    except Exception as exc:  # teardown never raises (Section 10.10)
        logger.warning(
            "agent session end after failed context fetch (best-effort)",
            extra={
                "event": "session_end_failed",
                "agent_session_id": agent_session_id,
                "project_id": project_id,
                "error_type": type(exc).__name__,
            },
        )
        return
    logger.info(
        "agent session ended after failed context fetch",
        extra={
            "event": "session_ended",
            "agent_session_id": agent_session_id,
            "project_id": project_id,
        },
    )
