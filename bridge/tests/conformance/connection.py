"""MCP client connections for the conformance runner (MT-2.11-01; Sections 10.2, 18).

The runner is the plan's "scripted client" (Section 18, MCP conformance row): it
speaks MCP to the bridge the way an agent client does, then drives the
Section 10.5 tool catalog. Two transports cover the Section 10.2 run modes the
compatibility matrix records:

* :class:`StdioMcpConnection` — spawns the bridge (``python -m
  orchestrator_bridge`` by default) and speaks newline-delimited JSON-RPC over
  its stdin/stdout, the launch shape Claude Code / OpenCode / Aider use.
* :class:`HttpMcpConnection` — raw streamable-HTTP JSON-RPC against a running
  bridge's ``/projects/{pid}/mcp`` endpoint, the VS Code Copilot shape.

Both are deliberately thin so the runner stays a reusable measuring instrument
(MT-2.11-01 risk note): no SDK client session, no silent retries — a broken
wire is a conformance *finding*, not something to paper over.

Every tool outcome is normalised into :class:`ToolCallResult`, which knows how
to read the Section 10.5 structured-error payload (``code``/``hint``/
``next_action``) out of the SDK's ``Error executing tool <name>: {json}``
message so checks can assert against the Section 9.2 catalog.
"""

from __future__ import annotations

import itertools
import json
import os
import subprocess  # noqa: S603 - list-args spawn of the local bridge, shell=False
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx2

__all__ = [
    "ConnectionBundle",
    "DEFAULT_RPC_TIMEOUT_SECONDS",
    "HttpMcpConnection",
    "McpConnection",
    "StdioMcpConnection",
    "ToolCallResult",
    "default_bridge_command",
    "stdio_bridge_env",
]

#: One bounded wait for any single JSON-RPC exchange (startup does a backend
#: session open; a live backend answers well inside this).
DEFAULT_RPC_TIMEOUT_SECONDS = 60.0

_ERROR_PREFIX = "Error executing tool "


@runtime_checkable
class McpConnection(Protocol):
    """The runner-facing MCP surface — both transports implement it."""

    def initialize(self) -> dict[str, Any]:
        """Handshake; returns the initialize result (instructions, serverInfo)."""
        ...

    def list_tools(self) -> list[dict[str, Any]]:
        """``tools/list`` — the advertised Section 10.5 catalog."""
        ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        """``tools/call`` — never raises on a tool error; normalises the result."""
        ...

    def list_prompts(self) -> list[dict[str, Any]]:
        """``prompts/list`` — may be empty; absence is a recorded fact (NFR-08)."""
        ...

    def get_prompt(self, name: str) -> dict[str, Any]:
        """``prompts/get`` — render one surfaced prompt."""
        ...

    def close(self) -> None:
        """Release the connection (process, socket); idempotent."""
        ...


@dataclass
class ToolCallResult:
    """One ``tools/call`` outcome in check-friendly shape (Section 10.5)."""

    name: str
    is_error: bool
    content: list[dict[str, Any]]

    @property
    def text_blocks(self) -> list[str]:
        """Every ``text`` content block, joined in order."""
        return [str(block.get("text", "")) for block in self.content if block.get("type") == "text"]

    @property
    def has_image_block(self) -> bool:
        """Whether an ``image`` content block arrived (vision path; FR-ATT-05)."""
        return any(block.get("type") == "image" for block in self.content)

    def payload(self) -> Any:
        """The decoded JSON payload of the first text block, else ``None``."""
        blocks = self.text_blocks
        if not blocks:
            return None
        try:
            return json.loads(blocks[0])
        except json.JSONDecodeError:
            return None

    def error_payload(self) -> dict[str, Any] | None:
        """The Section 10.5 structured failure (``code``/``hint``/``next_action``).

        The bridge wraps deliberate failures as
        ``Error executing tool <name>: {json}`` (``registration.payload_text``);
        anything else unparseable yields ``None`` and the check records the raw
        text instead of guessing a code.
        """
        if not self.is_error:
            return None
        for block in self.text_blocks:
            prefix, separator, tail = block.partition(": ")
            if separator and prefix.startswith(_ERROR_PREFIX):
                try:
                    decoded = json.loads(tail)
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, dict):
                    return decoded
        return None

    def error_code(self) -> str | None:
        """The observed Section 9.2 code of a failed call, else ``None``."""
        payload = self.error_payload()
        code = payload.get("code") if payload is not None else None
        return code if isinstance(code, str) else None


class _JsonRpcError(RuntimeError):
    """A transport-level protocol failure (not a tool error)."""


class StdioMcpConnection:
    """The bridge spawned as a child process, driven over stdio JSON-RPC.

    Mirrors how a local CLI client launches the bridge (Section 10.2 STDIO):
    the caller supplies the environment (manifest path, agent token, spool
    directory) and working directory; the runner owns only the wire.
    """

    def __init__(
        self,
        command: list[str],
        *,
        env: dict[str, str],
        cwd: Path | None = None,
        timeout: float = DEFAULT_RPC_TIMEOUT_SECONDS,
    ) -> None:
        self._command = list(command)
        self._env = dict(env)
        self._cwd = cwd
        self._timeout = timeout
        self._ids = itertools.count(1)
        self._process: subprocess.Popen[str] | None = None

    def open(self) -> None:
        """Spawn the bridge process (fail-fast on a non-starting command)."""
        if self._process is not None:  # pragma: no cover - open is called once
            return
        self._process = subprocess.Popen(  # noqa: S603 - list args, shell=False
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=self._env,
            cwd=str(self._cwd) if self._cwd is not None else None,
        )

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        process = self._process
        if process is None or process.poll() is not None or process.stdin is None:
            raise _JsonRpcError(f"bridge process is not running for {method}")
        stdin = process.stdin
        stdout = process.stdout
        if stdout is None:  # pragma: no cover - Popen guarantees pipes here
            raise _JsonRpcError("bridge stdout is not available")
        request_id = next(self._ids)
        stdin.write(
            json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            + "\n"
        )
        stdin.flush()
        # A watchdog kill turns a hung bridge into a clean timeout instead of
        # a stuck conformance run (the process exit closes stdout).
        watchdog = threading.Timer(self._timeout, process.kill)
        watchdog.start()
        try:
            for line in stdout:
                if not line.strip():
                    continue
                message = json.loads(line)
                if message.get("id") != request_id:
                    continue  # server notification or an earlier response
                if "error" in message:
                    raise _JsonRpcError(f"{method} failed: {message['error']}")
                result = message.get("result")
                return dict(result) if isinstance(result, dict) else {}
            raise _JsonRpcError(f"bridge exited before answering {method}")
        finally:
            watchdog.cancel()

    def initialize(self) -> dict[str, Any]:
        result = self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "orchestrator-conformance", "version": "1.0"},
            },
        )
        # The initialized notification completes the handshake (MCP spec).
        process = self._process
        if process is not None and process.stdin is not None:
            process.stdin.write(
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
            )
            process.stdin.flush()
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        tools = self._rpc("tools/list", {}).get("tools")
        return list(tools) if isinstance(tools, list) else []

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content")
        return ToolCallResult(
            name=name,
            is_error=result.get("isError") is True,
            content=list(content) if isinstance(content, list) else [],
        )

    def list_prompts(self) -> list[dict[str, Any]]:
        prompts = self._rpc("prompts/list", {}).get("prompts")
        return list(prompts) if isinstance(prompts, list) else []

    def get_prompt(self, name: str) -> dict[str, Any]:
        return self._rpc("prompts/get", {"name": name})

    def close(self) -> None:
        process = self._process
        if process is None:
            return
        self._process = None
        try:
            if process.stdin is not None:
                process.stdin.close()
            process.wait(timeout=15)
        except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
            process.kill()
            process.wait(timeout=15)


class HttpMcpConnection:
    """Streamable-HTTP MCP session against a running bridge (Section 10.2).

    One POST per JSON-RPC message to ``{base}/projects/{project_id}/mcp`` with
    the per-connection bearer token; the ``Mcp-Session-Id`` from initialize is
    echoed on every follow-up. Responses may be plain JSON or single-shot SSE
    (the transport negotiates), so both shapes decode here.
    """

    def __init__(
        self,
        base_url: str,
        project_id: str,
        token: str,
        *,
        timeout: float = DEFAULT_RPC_TIMEOUT_SECONDS,
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/projects/{project_id}/mcp"
        self._token = token
        self._timeout = timeout
        self._ids = itertools.count(1)
        self._session_id: str | None = None
        self._client = httpx2.Client(timeout=timeout)

    def _headers(self, *, with_session: bool = True) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self._token}",
        }
        if with_session and self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _decode(self, response: httpx2.Response) -> list[dict[str, Any]]:
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
        raise _JsonRpcError(f"unexpected MCP response content type {content_type!r}")

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = next(self._ids)
        response = self._client.post(
            self._endpoint,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            },
            headers=self._headers(),
        )
        if response.status_code != 200:
            raise _JsonRpcError(f"{method} answered HTTP {response.status_code}")
        for message in self._decode(response):
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise _JsonRpcError(f"{method} failed: {message['error']}")
            result = message.get("result")
            return dict(result) if isinstance(result, dict) else {}
        raise _JsonRpcError(f"no response with id {request_id} for {method}")

    def initialize(self) -> dict[str, Any]:
        request_id = next(self._ids)
        response = self._client.post(
            self._endpoint,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "orchestrator-conformance", "version": "1.0"},
                },
            },
            headers=self._headers(with_session=False),
        )
        if response.status_code != 200:
            raise _JsonRpcError(f"initialize answered HTTP {response.status_code}")
        self._session_id = response.headers.get("mcp-session-id")
        result: dict[str, Any] = {}
        for message in self._decode(response):
            if message.get("id") == request_id:
                result = dict(message.get("result") or {})
        self._client.post(
            self._endpoint,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=self._headers(),
        )
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        tools = self._rpc("tools/list", {}).get("tools")
        return list(tools) if isinstance(tools, list) else []

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content")
        return ToolCallResult(
            name=name,
            is_error=result.get("isError") is True,
            content=list(content) if isinstance(content, list) else [],
        )

    def list_prompts(self) -> list[dict[str, Any]]:
        prompts = self._rpc("prompts/list", {}).get("prompts")
        return list(prompts) if isinstance(prompts, list) else []

    def get_prompt(self, name: str) -> dict[str, Any]:
        return self._rpc("prompts/get", {"name": name})

    def close(self) -> None:
        self._client.close()


def stdio_bridge_env(
    *,
    manifest_path: Path,
    token: str,
    spool_dir: Path,
    api_base_url: str | None = None,
    session_capability: str | None = None,
    extra: dict[str, str] | None = None,
    base: dict[str, str] | None = None,
) -> dict[str, str]:
    """The environment for one stdio bridge spawn — ambient leakage stripped.

    The caller's shell may carry ``ORCHESTRATOR_*`` values from another stack
    (the hermetic-suite rule from ``tests/conftest.py``), so the child env is
    rebuilt: the inherited environment minus every ``ORCHESTRATOR_*`` key,
    plus exactly the values this run declares.
    """
    source = os.environ if base is None else base
    env = {key: value for key, value in source.items() if not key.startswith("ORCHESTRATOR_")}
    env.update(
        {
            "ORCHESTRATOR_BRIDGE_MANIFEST_PATH": str(manifest_path),
            "ORCHESTRATOR_AGENT_TOKEN": token,
            "ORCHESTRATOR_SPOOL_DIR": str(spool_dir),
            "ORCHESTRATOR_LOG_LEVEL": "WARNING",
        }
    )
    if api_base_url is not None:
        env["ORCHESTRATOR_API_BASE_URL"] = api_base_url
    if session_capability is not None:
        env["ORCHESTRATOR_BRIDGE_SESSION_CAPABILITY"] = session_capability
    env.update(extra or {})
    return env


def default_bridge_command() -> list[str]:
    """The module invocation of the bridge's own CLI entry (MT-2.1-04)."""
    return [sys.executable, "-m", "orchestrator_bridge"]


@dataclass
class ConnectionBundle:
    """Book-keeping for connections a run opened (closed with the report)."""

    opened: list[Any] = field(default_factory=list)
