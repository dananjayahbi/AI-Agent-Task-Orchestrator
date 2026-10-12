"""Backend agent-session lifecycle (parent plan Sections 10.3 steps 4–5, 9.2,
10.10, 19.3; MT-2.2-04, MT-2.2-05).

Steps 4–5 of the Section 10.3 startup sequence, strictly after the steps 1–3
binding of :func:`orchestrator_bridge.manifest.bind_startup`:

* **Step 4 — open.** :func:`open_session` mints an unguessable, bridge-issued
  session id (G-18), calls ``POST /api/v1/agent-sessions`` with the manifest's
  project resolved *by the backend from the token* (ADR-004: no ``project_id``
  in the body) and stores the returned id as the session-scoped
  ``agent_session_id`` every subsequent tool call uses (claim's fencing half,
  the end path). The session id is deliberately named ``agent_session_id``
  throughout — it is the backend's resource, not the MCP protocol handshake
  (MT-2.2-04 risk note).
* **Step 5 — context cache.** :func:`fetch_project_context` reads
  ``GET /api/v1/projects/{pid}`` (name, ``system_prompt_rules``) and
  ``GET /api/v1/projects/{pid}/policy`` (the policy summary) and holds only the
  Section 10.3 set — ``{name, policy summary, rules}`` — for the session
  lifetime: an in-process :class:`ProjectContext`, never written to disk
  (FR-SEC-04; "for the session"). Nothing is derived client-side
  (Section 19.3): the cache stores what the backend returned, verbatim.
* **End.** :func:`close_session` is the best-effort teardown counterpart:
  ``POST /agent-sessions/{id}/end`` with an aggressively bounded timeout and a
  single attempt — a failure logs and returns, never blocking process exit
  (Section 10.10); a crashed bridge simply never ends the session and the
  backend's staleness handling covers it.

The binding rule of Section 10.3 — "a mismatch aborts" — is enforced by the
server (FR-SEC-01) and mapped here (MT-2.2-05):
``AUTH_FORBIDDEN_PROJECT`` at the open becomes :class:`ProjectMismatchError`
(one clear, remedy-bearing startup abort for both detection paths); every
other backend rejection becomes :class:`SessionOpenError` with the canonical
code named. Retry with backoff is the WP-2.3 transport's bounded policy
(Section 10.10), so "transient" means "retried, then aborted clearly".
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, Final

from .api_errors import ApiError, ErrorCode, ErrorKind
from .config import RunMode, Settings
from .endpoints import endpoint
from .errors import INIT_COMMAND, ProjectMismatchError, SessionOpenError
from .logging import get_logger
from .manifest import StartupBinding
from .scrub import scrub_text
from .transport import ApiClient, SendFn

__all__ = [
    "AgentSession",
    "CAPABILITY_UNKNOWN",
    "CLIENT_NAME",
    "ProjectContext",
    "close_session",
    "fetch_project_context",
    "new_session_id",
    "open_session",
]

#: ``client_name`` sent on the open — identifies the bridge build to the owner.
CLIENT_NAME: Final = "orchestrator-bridge"
#: Section 10.4 capability negotiation is WP-2.5; until then "unknown"
#: (text-safe default — the backend's documented ``AgentSessionCreate`` default).
CAPABILITY_UNKNOWN: Final = "unknown"
#: Shutdown budget for the end call (MT-2.2-04: aggressively bounded — stdio
#: teardown races the agent's own process exit; log-and-continue beats hanging).
SESSION_END_TIMEOUT_SECONDS: Final = 2.0
#: One attempt on the way out; retries only delay exit (Section 10.10 posture).
SESSION_END_MAX_ATTEMPTS: Final = 1

#: Section 10.2 run modes map onto the backend's TransportEnum (stdio|http).
_TRANSPORT_BY_MODE: Final[Mapping[RunMode, str]] = {
    RunMode.STDIO: "stdio",
    RunMode.HTTP: "http",
    # The Merge Executor is not an agent worker; it never opens a session.
    # The mapping stays total so a future caller fails loudly, not silently.
    RunMode.MERGE_EXECUTOR: "http",
}

_LOGGER_COMPONENT = "session"


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """The Section 10.3 step-5 cache set — name, policy summary, rules.

    Exactly the three Section 10.3 fields; extra backend fields are not stored
    (MT-2.2-04 risk note: caching more invites client-side policy drift,
    Section 19.3). ``project_id`` comes from the bound manifest, not the
    response — the backend addresses the token's own project.
    """

    project_id: str
    name: str
    rules: str
    policy_summary: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AgentSession:
    """One bound backend session for this process (FR-MCP-06 lifetime)."""

    agent_session_id: str
    context: ProjectContext


def new_session_id() -> str:
    """Mint the bridge-issued session id (G-18): unguessable, header-safe.

    ``uuid4().hex`` is 32 lowercase hex chars — inside the backend's
    ``AgentSessionCreate`` pattern and far above its length floor; no
    project, host or timestamp is encoded (a session id must not leak
    anything; it is a capability, not a label).
    """
    return uuid.uuid4().hex


def _open_failure(binding: StartupBinding, error: ApiError) -> SessionOpenError:
    """Map a session-open rejection to the one startup-abort vocabulary.

    MT-2.2-05: both detection paths (server-verified mismatch being the
    authoritative one, FR-SEC-01) produce one user-facing message family, so
    the UX never forks. No token bytes in either branch.
    """
    if error.code is ErrorCode.AUTH_FORBIDDEN_PROJECT:
        message = (
            f"Startup aborted: this repository is bound to project "
            f"{binding.project_id}, but the configured agent token is not valid "
            f"for that project (backend code "
            f"{ProjectMismatchError.canonical_code}). One token is scoped to "
            "exactly one project (Section 10.3). Fix: point "
            "ORCHESTRATOR_AGENT_TOKEN (or the user-level bridge config) at the "
            f"token issued for {binding.project_id}, or run '{INIT_COMMAND}' in "
            f"the right repository. Backend message: {scrub_text(error.message)}"
        )
        return ProjectMismatchError(message)
    return SessionOpenError(
        f"Startup aborted: could not open an agent session for project "
        f"{binding.project_id} (backend code {error.code}): "
        f"{scrub_text(error.message)}. The bridge serves only bound sessions "
        "(Section 10.3 step 4); fix the reported cause and restart."
    )


def _malformed(binding: StartupBinding, where: str) -> ApiError:
    """A context/open response that is JSON but not the documented shape."""
    return ApiError(
        code=ErrorCode.SERVER_ERROR,
        message=f"response from {where} is not the documented shape",
        retryable=False,
        kind=ErrorKind.MALFORMED_RESPONSE,
        details={"reason": "unexpected_shape", "endpoint": where},
        correlation_id=None,
    )


def fetch_project_context(client: ApiClient, binding: StartupBinding) -> ProjectContext:
    """Step 5: fetch and shape the Section 10.3 context set (read-only cache).

    Two reads — the project row (name + ``system_prompt_rules``) and its
    policy row (the structured policy summary the backend returns). Backend
    failures surface as :class:`ApiError` unchanged: at startup
    :func:`open_session` maps them to :class:`SessionOpenError`; at tool time
    (the MT-2.4-06 cache-refresh path) the translator adds hint/next-action.
    """
    project = client.request("GET", endpoint("project_context").path.format(pid=binding.project_id))
    if not isinstance(project, Mapping):
        raise _malformed(binding, "GET /projects/{pid}")
    policy = client.request("GET", endpoint("project_policy").path.format(pid=binding.project_id))
    if not isinstance(policy, Mapping):
        raise _malformed(binding, "GET /projects/{pid}/policy")
    name = project.get("name")
    if not isinstance(name, str):
        raise _malformed(binding, "GET /projects/{pid}")
    rules = project.get("system_prompt_rules")
    return ProjectContext(
        project_id=binding.project_id,
        name=name,
        rules=rules if isinstance(rules, str) else "",
        policy_summary=dict(policy),
    )


def open_session(
    binding: StartupBinding,
    settings: Settings,
    *,
    client: ApiClient | None = None,
    mode: RunMode = RunMode.STDIO,
) -> AgentSession:
    """Step 4 (+ step 5): open the backend session, then cache its context.

    *client* is shared by the caller when the same :class:`ApiClient` will
    serve the tool calls (one client per process). Backend rejections raise
    :class:`ProjectMismatchError` (mismatch) or :class:`SessionOpenError`
    (everything else) — both ``BindingError``s, so the entry points' existing
    fail-fast path logs, scrubs and exits non-zero without a traceback.
    """
    api = client if client is not None else ApiClient.for_binding(binding, settings)
    logger = get_logger(_LOGGER_COMPONENT)
    session_id = new_session_id()
    payload = {
        "id": session_id,
        "client_name": CLIENT_NAME,
        "capability": CAPABILITY_UNKNOWN,
        "transport": _TRANSPORT_BY_MODE[mode],
    }
    try:
        response = api.request("POST", endpoint("session_open").path, body=payload)
        context = fetch_project_context(api, binding)
    except ApiError as exc:
        raise _open_failure(binding, exc) from None
    agent_session_id = (
        str(response.get("id"))
        if isinstance(response, Mapping) and isinstance(response.get("id"), str)
        else session_id
    )
    logger.info(
        "agent session opened",
        extra={
            "event": "session_opened",
            "agent_session_id": agent_session_id,
            "project_id": binding.project_id,
            "transport": payload["transport"],
        },
    )
    return AgentSession(agent_session_id=agent_session_id, context=context)


def close_session(
    binding: StartupBinding,
    settings: Settings,
    session: AgentSession,
    *,
    send: SendFn | None = None,
) -> bool:
    """Best-effort session end on clean shutdown — never raises, never blocks.

    Returns whether the backend confirmed the end. Any failure (backend down,
    timeout, non-2xx) is logged as one warning record and treated as "not
    ended": the bridge exits and the backend's staleness handling closes the
    row (MT-2.2-04; Section 10.10). ``send`` is the test seam (WP-2.3's
    injectable HTTP boundary); production uses the stdlib opener.
    """
    shutdown_settings = replace(
        settings,
        timeout_seconds=SESSION_END_TIMEOUT_SECONDS,
        retry_max_attempts=SESSION_END_MAX_ATTEMPTS,
    )
    api = ApiClient.for_binding(binding, shutdown_settings, send=send)
    path = endpoint("session_end").path.format(id=session.agent_session_id)
    logger = get_logger(_LOGGER_COMPONENT)
    try:
        api.request("POST", path)
    except ApiError as exc:
        logger.warning(
            "agent session end failed (best-effort; backend staleness handling covers it)",
            extra={
                "event": "session_end_failed",
                "agent_session_id": session.agent_session_id,
                "project_id": binding.project_id,
                "error_code": str(exc.code),
            },
        )
        return False
    logger.info(
        "agent session ended",
        extra={
            "event": "session_ended",
            "agent_session_id": session.agent_session_id,
            "project_id": binding.project_id,
        },
    )
    return True
