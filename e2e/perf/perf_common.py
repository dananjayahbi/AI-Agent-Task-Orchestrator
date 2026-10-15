"""Shared helpers for the WP-6.3 performance scenarios (MT-6.3-01).

Stdlib only, house style borrowed from ``e2e/sse_tunnel_stability.py``
(timed JSON client, framed SSE reader with a starvation guard). The
percentile method is copied verbatim from MT-1.10-06
(``backend/tests/perf/test_sse_delivery_load.py``) so fan-out numbers
stay comparable with the WP-1.10 reference run.

Scenario entry points live beside this file; execution instructions are
in ``docs/plan/perf-runbook.md`` (one documented command per scenario).
Results land in ``e2e/perf/results/`` (committed artifacts, no secrets);
the seed manifest with per-run agent tokens lands in ``e2e/perf/.run/``
(gitignored).
"""

from __future__ import annotations

import http.client
import json
import os
import platform
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PERF_DIR = Path(__file__).resolve().parent
REPO_ROOT = PERF_DIR.parent.parent
RESULTS_DIR = PERF_DIR / "results"
RUN_DIR = PERF_DIR / ".run"
MANIFEST_PATH = RUN_DIR / "manifest.json"
THRESHOLDS_PATH = PERF_DIR / "thresholds.json"
COMPOSE_BASE = REPO_ROOT / "infra" / "compose" / "compose.yaml"
COMPOSE_PERF_OVERRIDE = PERF_DIR / "compose.perf.yaml"
DEFAULT_COMPOSE_PROJECT = "wp63perf"
DEFAULT_API_BASE = "http://127.0.0.1:8063/api/v1"

API_PREFIX = "/api/v1"
# Paths are relative to the /api/v1 base the Api client prepends.
LOGIN_PATH = "/auth/login"
STREAM_PATH = "/events/stream"


class PerfError(RuntimeError):
    """A scenario could not run (bad input, stack down, seed missing)."""


def api_base(explicit: str | None = None) -> str:
    """Base URL of the perf stack's API (``PERF_API_BASE`` overrides)."""
    return (explicit or os.environ.get("PERF_API_BASE") or DEFAULT_API_BASE).rstrip("/")


def compose_argv(*args: str, project: str | None = None) -> list[str]:
    """``docker compose`` argv pinned to the perf stack and its override file.

    Always pass both ``-f`` files: the override adds the push-dispatch env
    passthrough (WP-6.3), and mixing file sets between ``up`` and later
    ``exec``/``logs`` calls would make compose flag the config as drifted.
    """
    return [
        "docker",
        "compose",
        "-p",
        project or os.environ.get("PERF_COMPOSE_PROJECT") or DEFAULT_COMPOSE_PROJECT,
        "-f",
        str(COMPOSE_BASE),
        "-f",
        str(COMPOSE_PERF_OVERRIDE),
        *args,
    ]


def load_thresholds() -> dict[str, Any]:
    """The plan-derived constants (MT-6.3-01 threshold configuration file)."""
    if not THRESHOLDS_PATH.exists():
        raise PerfError(f"threshold file missing: {THRESHOLDS_PATH}")
    return json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    """The seed manifest (owner + agent tokens/sessions) from the seed run."""
    manifest_path = path or MANIFEST_PATH
    if not manifest_path.exists():
        raise PerfError(
            f"seed manifest not found at {manifest_path} — run the seed first: "
            "python e2e/perf/seed_perf_fixture.py"
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def percentile(sorted_values: list[float], p: float) -> float:
    """Linear-interpolation percentile of an ascending list.

    Verbatim method from MT-1.10-06's delivery load test — same math, so
    WP-6.3 fan-out percentiles are directly comparable with WP-1.10's.
    """
    if not sorted_values:
        return 0.0
    position = (len(sorted_values) - 1) * p / 100.0
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def summarize(values_ms: list[float]) -> dict[str, Any]:
    """p50/p95/p99 (+count/max/min/mean) of a latency list, in ms."""
    ordered = sorted(values_ms)
    if not ordered:
        return {
            "count": 0,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "max_ms": None,
            "min_ms": None,
            "mean_ms": None,
        }
    return {
        "count": len(ordered),
        "p50_ms": round(percentile(ordered, 50), 2),
        "p95_ms": round(percentile(ordered, 95), 2),
        "p99_ms": round(percentile(ordered, 99), 2),
        "max_ms": round(ordered[-1], 2),
        "min_ms": round(ordered[0], 2),
        "mean_ms": round(sum(ordered) / len(ordered), 2),
    }


def judge(p95_ms: float | None, budget_ms: float) -> dict[str, Any]:
    """One machine-readable verdict: budget vs measured p95."""
    return {
        "budget_ms": budget_ms,
        "p95_ms": p95_ms,
        "pass": bool(p95_ms is not None and p95_ms < budget_ms),
    }


def environment_block() -> dict[str, Any]:
    """Host/versions block recorded with every results file (20.4 item 1)."""
    return {
        "host": platform.platform(),
        "python": sys.version.split()[0],
        "cpus": os.cpu_count(),
        "api_base": api_base(),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def write_results(stem: str, payload: dict[str, Any]) -> Path:
    """Persist one scenario's machine-readable results; return the path."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "scenario": stem,
        "mt": "MT-6.3-01",
        "environment": environment_block(),
        **payload,
    }
    path = RESULTS_DIR / f"{stem}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def verdict_line(label: str, verdict: dict[str, Any]) -> str:
    """The one-line pass/fail print every scenario emits (acceptance row)."""
    state = "PASS" if verdict["pass"] else "FAIL"
    return (
        f"{state} {label}: p95={verdict['p95_ms']}ms "
        f"budget={verdict['budget_ms']}ms"
    )


class Api:
    """Timed JSON client (owner-session or agent bearer, Section 15.4).

    ``request`` returns ``(payload, status, elapsed_ms)`` — the clock runs
    from just before the socket work to just after the body is parsed, so
    the NFR-02 latency numbers include transport, queueing and the full
    server round trip (the honest per-call latency).
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 60.0,
    ):
        base = api_base(base_url)
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise PerfError(f"api base must be an absolute http(s) URL, got {base!r}")
        self.scheme = parsed.scheme
        self.netloc = parsed.netloc
        self.base_path = parsed.path.rstrip("/")
        self.timeout = timeout
        self.token = token

    def login(self, username: str, password: str) -> dict[str, Any]:
        """POST /auth/login; store the owner-session token as a bearer."""
        payload, status, _ = self.request(
            "POST", LOGIN_PATH, body={"username": username, "password": password}
        )
        if status != 200 or not isinstance(payload, dict) or "token" not in payload:
            raise PerfError(f"login failed: status={status} payload={payload!r}")
        self.token = str(payload["token"])
        return payload

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        token: str | None = None,
        timeout: float | None = None,
    ) -> tuple[Any, int, float]:
        """One timed JSON round trip: ``(payload, status, elapsed_ms)``."""
        url = f"{self.scheme}://{self.netloc}{self.base_path}{path}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        bearer = token or self.token
        if bearer is not None:
            request.add_header("Authorization", f"Bearer {bearer}")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                raw = response.read()
                payload = json.loads(raw) if raw else None
                return payload, response.status, (time.perf_counter() - started) * 1000.0
        except urllib.error.HTTPError as exc:
            # 4xx/5xx: canonical error envelope — parsed, never raised, so
            # scenarios can count conflicts (409) as data, not crashes.
            raw = exc.read()
            try:
                payload = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                payload = raw.decode(errors="replace")
            return payload, exc.code, (time.perf_counter() - started) * 1000.0


class StreamStarved(RuntimeError):
    """An SSE connection went silent past the heartbeat tolerance."""


class SseConnection:
    """One open SSE connection: framed reads with a starvation guard.

    Mirrors ``sse_tunnel_stability.SseConnection`` (RISK-05 signature): a
    socket timeout bigger than the heartbeat gap means the stream stopped
    delivering — recorded as a fault, never silently retried.
    """

    def __init__(self, api: Api, path: str, gap_tolerance: float = 25.0) -> None:
        self.sock_timeout = gap_tolerance + 2.0
        if api.scheme == "https":
            connection: http.client.HTTPConnection = http.client.HTTPSConnection(
                api.netloc, timeout=self.sock_timeout, context=ssl.create_default_context()
            )
        else:
            connection = http.client.HTTPConnection(api.netloc, timeout=self.sock_timeout)
        headers = {"Accept": "*/*", "Cache-Control": "no-cache"}
        if api.token is not None:
            headers["Authorization"] = f"Bearer {api.token}"
        url = f"{api.base_path}{path}"
        connection.request("GET", url, headers=headers)
        self.connection = connection
        self.response = connection.getresponse()
        if self.response.status != 200:
            detail = self.response.read().decode(errors="replace")[:500]
            raise PerfError(
                f"stream open failed: status={self.response.status} body={detail!r}"
            )
        self.headers = {key.lower(): value for key, value in self.response.getheaders()}
        if "text/event-stream" not in self.headers.get("content-type", ""):
            raise PerfError(f"stream answered without text/event-stream: {self.headers!r}")
        self.label = path
        self.frames = 0
        self.last_frame_at = time.perf_counter()

    def read_frame(self) -> tuple[str, dict[str, Any] | None]:
        """One SSE frame: ``("heartbeat", None)`` or ``("event", envelope)``."""
        lines: list[bytes] = []
        while True:
            try:
                line = self.response.readline()
            except socket.timeout as exc:
                starved = time.perf_counter() - self.last_frame_at
                raise StreamStarved(
                    f"stream {self.label} starved: no frame for {starved:.1f}s "
                    f"(tolerance {self.sock_timeout - 2.0:.1f}s)"
                ) from exc
            if not line:
                raise PerfError(f"stream {self.label} closed by peer (EOF) mid-run")
            if line in (b"\n", b"\r\n"):
                if lines:
                    break
                continue
            lines.append(line.rstrip(b"\r\n"))
        self.last_frame_at = time.perf_counter()
        self.frames += 1
        if all(entry.startswith(b":") for entry in lines):
            return "heartbeat", None
        envelope: dict[str, Any] = {}
        for entry in lines:
            if entry.startswith(b"id:"):
                envelope["id"] = int(entry[3:].strip())
            elif entry.startswith(b"data:"):
                envelope.update(json.loads(entry[5:].strip()))
        if "id" not in envelope:
            raise PerfError(f"malformed SSE frame (no id): {envelope!r}")
        return "event", envelope

    def close(self) -> None:
        try:
            self.response.close()
        finally:
            self.connection.close()
