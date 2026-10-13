"""Shared fixtures for the bridge test suite (parent plan Section 20.4; MT-2.1-01).

Bridge tests are hermetic: ambient ``ORCHESTRATOR_*`` variables (a developer shell,
a Compose env file) must never leak into config-precedence or logging tests, and
the correlation scope must never bleed between tests (added with MT-2.1-03).

:data:`MINIMAL_MANIFEST` and :func:`write_manifest` (MT-2.2-01…03) give every
binding test the same hand-written known-good manifest — the smallest document
that satisfies ``schemas/manifest.v1.json`` — instead of hand-rolling JSON per file.

WP-2.2/2.4 add the two backend-facing seams: :class:`FakeBackend` injects
deterministic responses at the transport's send boundary (WP-2.3's one HTTP
seam — preferred mock point, no live backend), and :func:`stub_http_backend`
spins a real loopback HTTP server for the tests that must cross a socket
(entry-point subprocess handshakes).
"""

from __future__ import annotations

import dataclasses
import json
import logging as std_logging
import os
import threading
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from orchestrator_bridge import correlation
from orchestrator_bridge.config import RunMode, Settings
from orchestrator_bridge.manifest import StartupBinding
from orchestrator_bridge.session import AgentSession, ProjectContext
from orchestrator_bridge.tools.runtime import ToolRuntime
from orchestrator_bridge.transport import ApiClient, WireResponse

#: Never a real secret — fixture-only token for binding/redaction tests.
FIXTURE_TOKEN = "fixture-token-not-a-real-secret"

#: The plan Section 10.3 example values — hand-written known-good fixture.
MINIMAL_MANIFEST: dict[str, object] = {
    "schema_version": 1,
    "project_id": "PID00007",
    "project_name": "Tea Factory ERP",
    "orchestrator_api": "http://localhost:8000/api/v1",
    "default_branch": "main",
    "auto_branch_prefix": "feat/PID00007-",
    "audit_required_default": True,
}


@pytest.fixture
def minimal_manifest() -> dict[str, object]:
    """A fresh copy of the hand-written known-good manifest (Section 10.3 example)."""
    return dict(MINIMAL_MANIFEST)


@pytest.fixture
def write_manifest() -> Callable[..., Path]:
    """Write ``orchestrator.json`` (minimal or overridden) into a directory tree."""

    def _write(
        directory: Path,
        document: Mapping[str, object] | None = None,
        *,
        name: str = "orchestrator.json",
    ) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        payload = dict(MINIMAL_MANIFEST if document is None else document)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    return _write


@pytest.fixture
def isolated_init_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every ``default_user_config_path`` reader/writer at a temp file.

    WP-2.12 (``orchestrator init``) resolves the user config in three modules
    (``config`` for the loader, ``init.token_store`` for the writer,
    ``init.selftest`` for the verdict source); init tests must never touch a
    real profile config from this machine.
    """
    import orchestrator_bridge.config as _config
    from orchestrator_bridge.init import selftest as _selftest
    from orchestrator_bridge.init import token_store as _token_store

    path = tmp_path / "profile" / "orchestrator" / "bridge.toml"
    for module in (_config, _token_store, _selftest):
        monkeypatch.setattr(module, "default_user_config_path", lambda p=path: p)
    return path


@pytest.fixture(autouse=True)
def _hermetic_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip every ambient ``ORCHESTRATOR_*`` variable for one test."""
    for name in [name for name in os.environ if name.startswith("ORCHESTRATOR_")]:
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture(autouse=True)
def _isolated_correlation_scope() -> Iterator[None]:
    """Install an empty correlation scope; restore the outer one afterwards (MT-2.1-03)."""
    token = correlation.set_correlation_id("")
    yield
    correlation.reset_correlation_id(token)


@pytest.fixture(autouse=True)
def _reset_bridge_logging() -> Iterator[None]:
    """Leave no bridge handlers/levels behind after a logging test (MT-2.1-03)."""
    yield
    logger = std_logging.getLogger("bridge")
    logger.handlers.clear()
    logger.setLevel(std_logging.NOTSET)
    logger.propagate = True


# --- backend-facing test seams (WP-2.2/2.4) -----------------------------------


def json_wire(status: int, payload: Any, headers: Mapping[str, str] | None = None) -> WireResponse:
    """One wire response carrying a JSON body (``payload=None`` → empty body)."""
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    wire_headers = {"content-type": "application/json"}
    wire_headers.update({key.lower(): value for key, value in (headers or {}).items()})
    return WireResponse(status=status, headers=wire_headers, body=body)


def envelope_wire(
    status: int,
    code: str,
    message: str,
    *,
    retryable: bool = False,
    details: Mapping[str, Any] | None = None,
    correlation_id: str = "corr-fixture",
) -> WireResponse:
    """One wire failure carrying the standard Section 9.2 error envelope."""
    return json_wire(
        status,
        {
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "details": dict(details) if details is not None else None,
                "correlation_id": correlation_id,
            }
        },
    )


@dataclass
class RecordedCall:
    """One call observed at the send seam: verb, URL, headers, decoded body."""

    method: str
    url: str
    headers: Mapping[str, str]
    body: Any

    @property
    def path(self) -> str:
        return urlsplit(self.url).path

    @property
    def query(self) -> str:
        return urlsplit(self.url).query


#: A canned response: static pair, or callable(body) -> (status, payload).
RouteResponse = tuple[int, Any] | Callable[[Any], tuple[int, Any]]


@dataclass
class FakeBackend:
    """Deterministic fake at the transport's send seam (WP-2.3 injectable).

    Routes are keyed by ``(METHOD, path)`` (query stripped); an unplanned call
    raises so a handler's request surface stays pinned. Responses may be
    dynamic (a callable of the decoded request body) for echo-style endpoints
    like the session open.
    """

    base_url: str = "http://bridge.invalid/api/v1"
    routes: dict[tuple[str, str], RouteResponse] = field(default_factory=dict)
    dynamic: list[tuple[str, str, RouteResponse]] = field(default_factory=list)
    calls: list[RecordedCall] = field(default_factory=list)

    def route(self, method: str, path: str, status: int, payload: Any) -> None:
        """Register a static response for one (method, path)."""
        self.routes[(method.upper(), path)] = (status, payload)

    def route_fn(self, method: str, path: str, respond: Callable[[Any], tuple[int, Any]]) -> None:
        """Register a dynamic response for one (method, path)."""
        self.routes[(method.upper(), path)] = respond

    def route_dynamic(self, method: str, path_suffix: str, response: RouteResponse) -> None:
        """Register a fallback for paths *ending in* ``path_suffix``.

        The bridge mints session ids at runtime, so ``.../agent-sessions/{id}/
        end`` cannot be keyed exactly up front (WP-2.9 connection teardown);
        consulted only when the exact route misses — existing tests are
        untouched while the list stays empty.
        """
        self.dynamic.append((method.upper(), path_suffix, response))

    def calls_to(self, method: str, path: str) -> list[RecordedCall]:
        return [call for call in self.calls if call.method == method and call.path == path]

    def send(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> WireResponse:
        """The ``SendFn`` seam: record, then answer the registered route."""
        del timeout  # the fake never times out; real timeouts are WP-2.3-tested
        payload = json.loads(body) if body else None
        self.calls.append(
            RecordedCall(method=method.upper(), url=url, headers=dict(headers), body=payload)
        )
        path = urlsplit(url).path
        route = self.routes.get((method.upper(), path))
        if route is None:
            for verb, suffix, fallback in self.dynamic:
                if verb == method.upper() and path.endswith(suffix):
                    route = fallback
                    break
        if route is None:
            raise AssertionError(f"unplanned backend call: {method} {path}")
        if callable(route):
            status, response_payload = route(payload)
        else:
            status, response_payload = route
        return json_wire(status, response_payload)


class FakeRunServer:
    """Stands in for MCPServer so stdio.run() can be exercised without blocking."""

    def __init__(self) -> None:
        self.transport: str | None = None

    def run(self, transport: str = "stdio") -> None:
        self.transport = transport


def build_settings(**overrides: Any) -> Settings:
    """Hermetic settings for handler tests: no retries, tiny timeouts."""
    base = Settings(
        api_base_url="http://bridge.invalid/api/v1",
        agent_token=FIXTURE_TOKEN,
        manifest_path=None,
        log_level="INFO",
        log_format="json",
        mode=RunMode.STDIO,
        timeout_seconds=5.0,
        max_response_mb=1.0,
        retry_max_attempts=1,
        retry_base_delay_seconds=0.0,
        merge_repo_paths=(),
        http_host="127.0.0.1",
        http_port=0,
        http_max_connections=16,
        http_idle_timeout_seconds=900.0,
    )
    if not overrides:
        return base
    return dataclasses.replace(base, **overrides)


def build_binding() -> StartupBinding:
    """The hand-written Section 10.3 manifest as a bound startup binding."""
    return StartupBinding(manifest_path=Path("orchestrator.json"), manifest=dict(MINIMAL_MANIFEST))


def build_runtime(
    fake: FakeBackend | None = None,
    *,
    context: ProjectContext | None = None,
    settings: Settings | None = None,
) -> ToolRuntime:
    """A runtime bound to the fixture project over the fake transport."""
    backend = fake if fake is not None else FakeBackend()
    binding = build_binding()
    client = ApiClient.for_binding(binding, settings or build_settings(), send=backend.send)
    session = AgentSession(
        agent_session_id="fixture-session-0001",
        context=context
        if context is not None
        else ProjectContext(
            project_id="PID00007",
            name="Tea Factory ERP",
            rules="Project rule: run the tests.",
            policy_summary={"max_concurrent_tasks": 1, "lease_duration_minutes": 45},
        ),
    )
    return ToolRuntime.from_session(binding, client, session)


@pytest.fixture
def fake_backend() -> FakeBackend:
    """A fresh send-seam fake per test."""
    return FakeBackend()


@pytest.fixture
def runtime(fake_backend: FakeBackend) -> ToolRuntime:
    """A fixture-project runtime over the send-seam fake (context cached)."""
    return build_runtime(fake_backend)


# --- loopback HTTP stub for entry-point tests ----------------------------------


@dataclass
class StubHttpBackend:
    """A real loopback HTTP server answering the Section 10.3 startup calls.

    Used where a socket is required (subprocess handshakes). Responses use the
    same ``(status, payload)``/callable vocabulary as :class:`FakeBackend`,
    keyed by ``(METHOD, path)``; the session-end path (dynamic id) registers
    under ``(POST, "/__session_end__")``. An unplanned request answers a 404
    envelope — a startup call the bridge should not have made is visible but
    not fatal to the test process.
    """

    server: ThreadingHTTPServer
    responses: dict[tuple[str, str], RouteResponse]
    requests: list[RecordedCall]

    @property
    def origin(self) -> str:
        host = str(self.server.server_address[0])
        port = int(self.server.server_address[1])
        return f"http://{host}:{port}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class _StubHandler(BaseHTTPRequestHandler):
    """One request → record it, then answer from the server's responses."""

    server_version = "BridgeStub/1.0"

    def log_message(self, *args: Any) -> None:  # noqa: ARG002 - keep pytest output clean
        return

    def _handle(self) -> None:
        stub: StubHttpBackend = self.server.stub  # type: ignore[attr-defined]
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        payload = json.loads(raw) if raw else None
        path = urlsplit(self.path).path
        key = (self.command, path)
        if key not in stub.responses and self.command == "POST" and path.endswith("/end"):
            key = (self.command, "/__session_end__")
        stub.requests.append(
            RecordedCall(
                method=self.command, url=self.path, headers=dict(self.headers), body=payload
            )
        )
        route = stub.responses.get(key)
        if route is None:
            status, body = (
                400,
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"stub has no route for {self.command} {path}",
                        "retryable": False,
                        "details": None,
                        "correlation_id": "corr-stub",
                    }
                },
            )
        else:
            status, response_payload = route(payload) if callable(route) else route
            body = response_payload
        encoded = b"" if body is None else json.dumps(body).encode("utf-8")
        self.send_response(status)
        if encoded:
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if encoded:
            self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._handle()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._handle()


def _default_stub_responses() -> dict[tuple[str, str], RouteResponse]:
    """The Section 10.3 happy path for the fixture project (PID00007)."""
    return {
        ("POST", "/api/v1/agent-sessions"): (
            lambda body: (
                201,
                {
                    "id": body["id"],
                    "project_id": "PID00007",
                    "transport": body["transport"],
                },
            )
        ),
        ("GET", "/api/v1/projects/PID00007"): (
            200,
            {"id": "PID00007", "name": "Tea Factory ERP", "system_prompt_rules": "Project rule."},
        ),
        ("GET", "/api/v1/projects/PID00007/policy"): (
            200,
            {"max_concurrent_tasks": 1, "lease_duration_minutes": 45},
        ),
        ("POST", "/__session_end__"): (200, None),
    }


@pytest.fixture
def stub_http_backend() -> Iterator[StubHttpBackend]:
    """A running loopback stub for the startup HTTP calls; stopped after use."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    stub = StubHttpBackend(server=server, responses=_default_stub_responses(), requests=[])
    server.stub = stub  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        stub.stop()
        thread.join(timeout=5)


@pytest.fixture
def stub_manifest_env(
    tmp_path: Path, write_manifest: Callable[..., Path], stub_http_backend: StubHttpBackend
) -> dict[str, str]:
    """Env for a stdio entry point bound to the stub backend (fixture token)."""
    manifest = write_manifest(
        tmp_path / "bound-repo",
        {**MINIMAL_MANIFEST, "orchestrator_api": f"{stub_http_backend.origin}/api/v1"},
    )
    return {
        "ORCHESTRATOR_BRIDGE_MANIFEST_PATH": str(manifest),
        "ORCHESTRATOR_AGENT_TOKEN": FIXTURE_TOKEN,
    }
