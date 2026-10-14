"""One-shot inspector-evidence runner (WP-2.8 / WP-3.8 acceptance).

Boots a loopback stub for the Section 10.3 startup calls (same response
table as conftest's ``stub_http_backend``), writes a temp manifest + token,
then runs the MCP inspector CLI over stdio against the real bridge process
— printing prompts/list, a get-prompt render and tools/list. Used once for
the changelogs' recorded inspector runs; the CI-authoritative checks are
the stdio wire tests in tests/test_prompts.py and tests/test_entrypoints.py.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.conftest import (  # noqa: E402
    FIXTURE_TOKEN,
    StubHttpBackend,
    _default_stub_responses,
    _StubHandler,
)


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    stub = StubHttpBackend(server=server, responses=_default_stub_responses(), requests=[])
    server.stub = stub  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            manifest = {
                "schema_version": 1,
                "project_id": "PID00007",
                "project_name": "Tea Factory ERP",
                "orchestrator_api": f"{stub.origin}/api/v1",
                "default_branch": "main",
                "auto_branch_prefix": "feat/PID00007-",
                "audit_required_default": True,
            }
            manifest_path = Path(tmp, "orchestrator.json")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            env = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith("ORCHESTRATOR_")
            }
            env.update(
                {
                    "ORCHESTRATOR_BRIDGE_MANIFEST_PATH": str(manifest_path),
                    "ORCHESTRATOR_AGENT_TOKEN": FIXTURE_TOKEN,
                }
            )
            npx = shutil.which("npx") or shutil.which("npx.cmd")
            if npx is None:
                print("npx not found on PATH — Node tooling required", file=sys.stderr)
                return 2
            # Config-file mode: the 2026 inspector CLI drops target args
            # (-m orchestrator_bridge) when the server is passed as a
            # positional, so the command/args/env go into a session config
            # file instead (--config is read-only, served as-is).
            config_path = Path(tmp, "inspector-config.json")
            config = {
                "mcpServers": {
                    "orchestrator-bridge": {
                        "command": sys.executable,
                        "args": ["-m", "orchestrator_bridge"],
                        "env": env,
                    }
                }
            }
            config_path.write_text(json.dumps(config), encoding="utf-8")
            base = [
                npx,
                "-y",
                "@modelcontextprotocol/inspector@latest",
                "--cli",
                "--config",
                str(config_path),
                "--server",
                "orchestrator-bridge",
                "--protocol-era",
                "auto",
                "--connect-timeout",
                "30000",
            ]
            for method, extra in (
                ("prompts/list", []),
                ("prompts/get", ["--prompt-name", "orchestrator:start_work"]),
                ("tools/list", []),
            ):
                print(f"\n=== {method} ===")
                result = subprocess.run(
                    [*base, "--format", "json", "--method", method, *extra],
                    env=env,
                    cwd=str(Path(__file__).resolve().parent.parent),
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if result.returncode != 0:
                    print(result.stdout[-3000:])
                    print(result.stderr[-2000:], file=sys.stderr)
                    return result.returncode
                payload = json.loads(result.stdout)
                if "result" in payload:  # --format json wraps the body
                    payload = payload["result"]
                if method == "prompts/list":
                    for prompt in payload["prompts"]:
                        print(f"prompt: {prompt['name']} — {prompt['description'][:80]}")
                elif method == "prompts/get":
                    text = payload["messages"][0]["content"]["text"]
                    print(
                        f"description: {payload['description'][:80]}\n"
                        f"message[0] ({len(text)} chars): {text[:400]}..."
                    )
                else:
                    names = [tool["name"] for tool in payload["tools"]]
                    print(f"{len(names)} tools: {', '.join(names)}")
        return 0
    finally:
        stub.stop()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
