"""Shared harness for the WP-2.9 HTTP/SSE service tests (Section 20.4).

Everything here runs the **real** service — the production entry
(``entrypoints.http.run``), uvicorn on a loopback ephemeral port, the real
ASGI app — because MT-2.9-04 demands "the real multi-connection server (not a
mocked transport)". Only the bridge→backend leg is a seam (the WP-2.3
``SendFn``): MCP traffic crosses sockets; backend answers stay deterministic
and hermetic.

Pieces:

* :func:`running_bridge` — start/stop context manager around
  ``entrypoints.http.run`` in a worker thread, capturing the structured log
  buffer and the ``uvicorn.Server`` handle (``should_exit`` = graceful stop).
* :class:`McpHttpClient` — a raw streamable-HTTP JSON-RPC client (initialize,
  notifications, ``tools/*``, SSE GET, DELETE) with per-request control of
  the ``Authorization``/``Mcp-Session-Id`` headers, so binding rejections can
  be provoked deliberately.
* :func:`free_port` — a loopback port released before use (races are
  acceptable in tests; the bind-failure test re-checks deterministically).
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import itertools
import json
import socket
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx2

from orchestrator_bridge.config import RunMode, Settings
from orchestrator_bridge.entrypoints import http as http_entry
from orchestrator_bridge.logging import configure_logging
from tests.conftest import FakeBackend, build_settings

__all__ = [
    "FakeClock",
    "McpHttpClient",
    "RunningBridge",
    "decode_rpc_response",
    "free_port",
    "happy_backend",
    "http_settings",
    "running_bridge",
    "service_envelope",
    "wait_for",
]

_STARTUP_TIMEOUT_SECONDS = 20.0
_STOP_TIMEOUT_SECONDS = 20.0


def http_settings(**overrides: Any) -> Settings:
    """HTTP-mode settings on a fresh loopback port (hermetic, tiny retries)."""
    base = build_settings(mode=RunMode.HTTP, http_port=free_port())
    if not overrides:
        return base
    return dataclasses.replace(base, **overrides)


def wait_for(
    predicate: Callable[[], bool], *, timeout: float = 5.0, message: str = "condition"
) -> None:
    """Poll until *predicate* holds — teardown after a response is async.

    A client's DELETE response is flushed *before* the server-side finalize
    finishes (the manager stop and backend session end follow), so tests
    assert server-side cleanup with a bounded wait rather than a sleep.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError(f"timed out after {timeout}s waiting for {message}")


class FakeClock:
    """Injected lifecycle clock: tests advance it, the sweeper reads it."""

    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


#: Authorization scheme, spelled once as a bare token (the runtime's output
#: scrubber masks bearer-looking literals in tool payloads; keeping the value
#: free of a trailing token on the same line keeps this file honest).
_BEARER_SCHEME = "Bearer"


def service_envelope(code: str, message: str, *, retryable: bool = False) -> dict[str, Any]:
    """A Section 9.2 error envelope as a FakeBackend payload."""
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": None,
            "correlation_id": "corr-http-fixture",
        }
    }


def happy_backend(*projects: tuple[str, str]) -> FakeBackend:
    """A :class:`tests.conftest.FakeBackend` with the Section 10.3 happy path.

    Registers the session-open echo (transport carried through), the
    best-effort ``/end`` fallback for any bridge-minted session id, and each
    ``(project id, name)`` pair's context + policy reads — enough for any
    number of simultaneously bound HTTP connections.
    """
    fake = FakeBackend()
    fake.route_fn(
        "POST",
        "/api/v1/agent-sessions",
        lambda body: (
            201,
            {
                "id": body["id"],
                "project_id": "bound-from-token",
                "transport": body["transport"],
            },
        ),
    )
    fake.route_dynamic("POST", "/end", (200, None))
    for project_id, name in projects:
        fake.route(
            "GET",
            f"/api/v1/projects/{project_id}",
            200,
            {"id": project_id, "name": name, "system_prompt_rules": f"Rules for {name}."},
        )
        fake.route(
            "GET",
            f"/api/v1/projects/{project_id}/policy",
            200,
            {"max_concurrent_tasks": 1, "lease_duration_minutes": 45},
        )
        fake.route(
            "GET",
            f"/api/v1/projects/{project_id}/work",
            200,
            {"results": [], "next_cursor": None},
        )
    return fake


def free_port() -> int:
    """A loopback TCP port, released for the bridge to bind."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def decode_rpc_response(response: httpx2.Response) -> list[dict[str, Any]]:
    """Decode one MCP POST response — JSON body or single-shot SSE stream."""
    content_type = response.headers.get("content-type", "").lower()
    if content_type.startswith("application/json"):
        if not response.content:
            return []
        payload = response.json()
        return [payload] if isinstance(payload, dict) else list(payload)
    if content_type.startswith("text/event-stream"):
        messages: list[dict[str, Any]] = []
        for block in response.text.split("\n\n"):
            data_lines = [
                line[len("data:") :].lstrip()
                for line in block.splitlines()
                if line.startswith("data:")
            ]
            if data_lines:
                messages.append(json.loads("\n".join(data_lines)))
        return messages
    raise AssertionError(
        f"unexpected MCP response content type {content_type!r}: {response.text!r}"
    )


def _result_of(messages: list[dict[str, Any]], request_id: int) -> dict[str, Any]:
    for message in messages:
        if message.get("id") == request_id:
            if "error" in message:
                raise AssertionError(f"JSON-RPC error: {message['error']}")
            return dict(message["result"])
    raise AssertionError(f"no response with id {request_id}: {messages!r}")


class McpHttpClient:
    """Raw streamable-HTTP MCP client with explicit header control."""

    def __init__(self, base_url: str, project_id: str, token: str) -> None:
        self.endpoint = f"{base_url}/projects/{project_id}/mcp"
        self.project_id = project_id
        self.token = token
        self.session_id: str | None = None
        self.protocol_version: str | None = None
        self._ids = itertools.count(1)
        self._client = httpx2.Client(timeout=15.0)

    # --- wire helpers ---------------------------------------------------------

    def _headers(
        self,
        *,
        token: str | None = None,
        session_id: str | None | object = ...,
        auth_header: str | None = None,
        omit_auth: bool = False,
    ) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if not omit_auth:
            headers["Authorization"] = (
                auth_header
                if auth_header is not None
                else f"{_BEARER_SCHEME} {self.token if token is None else token}"
            )
        resolved = self.session_id if session_id is ... else session_id
        if resolved:
            headers["Mcp-Session-Id"] = str(resolved)
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        return headers

    def raw_post(
        self,
        payload: dict[str, Any],
        *,
        token: str | None = None,
        session_id: str | None | object = ...,
        project_id: str | None = None,
        auth_header: str | None = None,
        omit_auth: bool = False,
    ) -> httpx2.Response:
        """One raw POST (negative tests may override any header or path)."""
        endpoint = (
            self.endpoint
            if project_id is None
            else (self.endpoint.rsplit("/projects/", 1)[0] + f"/projects/{project_id}/mcp")
        )
        return self._client.post(
            endpoint,
            json=payload,
            headers=self._headers(
                token=token,
                session_id=session_id,
                auth_header=auth_header,
                omit_auth=omit_auth,
            ),
        )

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = next(self._ids)
        response = self.raw_post(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        assert response.status_code == 200, (response.status_code, response.text)
        return _result_of(decode_rpc_response(response), request_id)

    # --- protocol -------------------------------------------------------------

    def initialize(self) -> dict[str, Any]:
        """Handshake; records the session id and negotiated protocol version.

        A fresh initialize never carries a session id — a reconnect after a
        DELETE must open a *new* binding (NFR-04), not resurrect the dead one.
        """
        request_id = next(self._ids)
        response = self.raw_post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "wp-2-9-test", "version": "1.0"},
                },
            },
            session_id=None,
        )
        assert response.status_code == 200, (response.status_code, response.text)
        self.session_id = response.headers.get("mcp-session-id")
        assert self.session_id, "initialize response must assign Mcp-Session-Id"
        result = _result_of(decode_rpc_response(response), request_id)
        self.protocol_version = str(result.get("protocolVersion") or "2025-06-18")
        return result

    def notify_initialized(self) -> None:
        response = self.raw_post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        assert response.status_code in (200, 202), response.status_code

    def connect(self) -> dict[str, Any]:
        """initialize + initialized notification; returns the init result."""
        result = self.initialize()
        self.notify_initialized()
        return result

    def tools_list(self) -> list[dict[str, Any]]:
        return list(self._rpc("tools/list", {})["tools"])

    def tools_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._rpc("tools/call", {"name": name, "arguments": arguments})

    def call_payload(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """The decoded JSON payload a tool result carries as text content."""
        result = self.tools_call(name, arguments or {})
        content = result["content"][0]
        assert content["type"] == "text", content
        return json.loads(content["text"])

    def call_error_payload(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """The decoded Section 9.2-style payload of a failed tool call."""
        result = self.tools_call(name, arguments or {})
        assert result.get("isError"), result
        text = result["content"][0]["text"]
        _prefix, separator, tail = text.partition(": ")
        assert separator, text
        return json.loads(tail)

    def delete_session(self) -> int:
        assert self.session_id, "no session to DELETE"
        response = self._client.delete(
            self.endpoint, headers=self._headers(session_id=self.session_id)
        )
        return response.status_code

    @contextlib.contextmanager
    def sse_stream(self) -> Iterator[httpx2.Response]:
        """Open the GET (server→client SSE) stream for this session."""
        assert self.session_id, "initialize first"
        with self._client.stream("GET", self.endpoint, headers=self._headers()) as response:
            yield response

    def health(self) -> httpx2.Response:
        base = self.endpoint.rsplit("/projects/", 1)[0]
        return self._client.get(f"{base}/health")

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> McpHttpClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


@dataclass
class RunningBridge:
    """A live HTTP service: logs, server handle, registered clients."""

    port: int
    logs: io.StringIO
    server: Any
    thread: threading.Thread
    _exit_code: dict[str, int]
    clients: list[McpHttpClient] = field(default_factory=list)
    _stopped: bool = False

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def client(self, project_id: str, token: str) -> McpHttpClient:
        """A client registered for automatic close at stop (drain = no hangs)."""
        client = McpHttpClient(self.base_url, project_id, token)
        self.clients.append(client)
        return client

    def log_records(self) -> list[dict[str, Any]]:
        records = []
        for line in self.logs.getvalue().splitlines():
            line = line.strip()
            if line.startswith("{"):
                records.append(json.loads(line))
        return records

    def stop(self) -> int:
        """Graceful shutdown: close clients, ask uvicorn to exit, join."""
        if self._stopped:
            return self._exit_code.get("code", -1)
        self._stopped = True
        for client in self.clients:
            client.close()
        self.server.should_exit = True
        self.thread.join(timeout=_STOP_TIMEOUT_SECONDS)
        assert not self.thread.is_alive(), "bridge did not shut down in time"
        assert "code" in self._exit_code, "bridge thread exited before run() returned"
        return self._exit_code["code"]


@contextlib.contextmanager
def running_bridge(
    settings: Settings,
    *,
    send: Callable[..., Any] | None = None,
    time_func: Callable[[], float] | None = None,
    sweep_tick_seconds: float = 30.0,
) -> Iterator[RunningBridge]:
    """Start ``entrypoints.http.run`` on a worker thread; stop it on exit."""
    assert settings.http_port != 0, "give the test a concrete free_port()"
    logs = io.StringIO()
    configure_logging(settings, stream=logs, mode=RunMode.HTTP)
    captured: dict[str, Any] = {}
    exit_code: dict[str, int] = {}

    def _on_server(server: Any) -> None:
        captured["server"] = server

    def _serve() -> None:
        exit_code["code"] = http_entry.run(
            settings,
            on_server=_on_server,
            send=send,
            sweep_tick_seconds=sweep_tick_seconds,
            **({"time_func": time_func} if time_func is not None else {}),
        )

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        server = captured.get("server")
        if server is not None and getattr(server, "started", False):
            break
        if not thread.is_alive():
            raise AssertionError(
                f"bridge exited during startup (code={exit_code}); logs:\n{logs.getvalue()}"
            )
        time.sleep(0.02)
    else:  # noqa: PERF203 - polling loop is the readiness protocol
        raise AssertionError(f"bridge never started; logs:\n{logs.getvalue()}")

    server = captured["server"]
    host, port, *_ = server.servers[0].sockets[0].getsockname()
    assert host  # bound for real
    bridge = RunningBridge(
        port=int(port),
        logs=logs,
        server=server,
        thread=thread,
        _exit_code=exit_code,
    )
    try:
        yield bridge
    finally:
        bridge.stop()
