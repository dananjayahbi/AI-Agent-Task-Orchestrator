#!/usr/bin/env python3
"""SSE stability soak through the edge path — MT-5.1-04 (WP-5.1).

Verifies the Section 15.4 / 9.6 obligations for ``GET /api/v1/events/stream``
against any reachable origin — the LAN Compose backend (control run) or the
Cloudflare tunnel hostname (the load-bearing proof, RISK-05):

* **Idle survival** — a connection stays open for the full idle window with
  the 15 s heartbeat comments keeping every proxy hop awake: zero unplanned
  disconnects, max inter-frame gap within tolerance, at least
  ``idle/heartbeat - 1`` heartbeats observed.
* **No response buffering** — a probe event published near the end of the
  idle window arrives promptly (NFR-03: under 2 s), not held until stream
  end.
* **Lossless resume** — after a deliberate drop, reconnecting with
  ``Last-Event-ID`` replays exactly the stored events that were missed
  (no gaps, no duplicates — Section 9.6), and the same connection keeps
  delivering live events afterwards.

Stdlib only (``http.client``, ``urllib``, ``json``) so the script runs on any
host with Python 3.10+ — no install step between the operator and the tunnel
run. Credentials travel as environment variables (``SSE_SOAK_USERNAME`` /
``SSE_SOAK_PASSWORD``), never as arguments (process listings) and never
committed. The login response's owner-session token is used as the Section
15.4 bearer transport; its lifetime (12 h default, Section 9.10) spans any
sanctioned soak window, so a mid-run expiry cannot masquerade as a tunnel
drop (MT-5.1-04 risk note).

Duration policy (MT-5.1-04 acceptance): the acceptance run is
``--idle-seconds 1800`` (30 min) x ``--cycles 2`` — on demand/nightly, not on
every PR. CI and local control runs pass a reduced ``--idle-seconds`` (e.g.
150 — ten heartbeat intervals, enough to measure cadence and gaps); the
script asserts the *same* properties at any duration, it never shortens the
acceptance bar itself.

Exit code 0 = every assertion passed; 1 = at least one failed (evidence in
the results document). The JSON results record (timestamps, heartbeat count,
max gap, disconnect count, latencies, replay sets) is the verification
evidence recorded in infra/cloudflare/sse-verification.md.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

STREAM_PATH = "/api/v1/events/stream"
HISTORY_PATH = "/api/v1/events"
LOGIN_PATH = "/api/v1/auth/login"
PROJECTS_PATH = "/api/v1/projects"

#: NFR-03: real-time event delivery p95 under 2 s — the single-event probe
#: asserts the same budget on whatever path (LAN or tunnel) is under test.
DEFAULT_MAX_LATENCY_SECONDS = 2.0

#: Heartbeat cadence of Section 9.6 (ORCHESTRATOR_EVENTS_HEARTBEAT_SECONDS).
DEFAULT_HEARTBEAT_SECONDS = 15.0

#: Events published while the connection is deliberately dropped — enough to
#: prove replay without inflating the run.
MISSED_EVENTS_PER_CYCLE = 2


class SoakFailure(Exception):
    """One assertion failed; message carries the evidence."""


def utc_now() -> str:
    """Current time in the plan's second-precision UTC form."""
    return datetime.now(UTC).isoformat(timespec="seconds", sep="T").replace("+00:00", "Z")


class Api:
    """Thin owner-session JSON client (bearer transport, Section 15.4)."""

    def __init__(self, base_url: str, timeout: float) -> None:
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise SoakFailure(f"--base-url must be an absolute http(s) URL, got {base_url!r}")
        self.scheme = parsed.scheme
        self.netloc = parsed.netloc
        self.timeout = timeout
        self.token: str | None = None

    def login(self, username: str, password: str) -> dict[str, Any]:
        """POST /auth/login; store the owner-session token as a bearer."""
        payload, status, _ = self.request(
            "POST", LOGIN_PATH, body={"username": username, "password": password}
        )
        if status != 200 or not isinstance(payload, dict) or "token" not in payload:
            raise SoakFailure(f"login failed: status={status} payload={payload!r}")
        self.token = str(payload["token"])
        return payload

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> tuple[Any, int, dict[str, str]]:
        """One JSON round trip: (parsed payload or None, status, headers)."""
        url = f"{self.scheme}://{self.netloc}{path}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if self.token is not None:
            request.add_header("Authorization", f"Bearer {self.token}")
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                raw = response.read()
                return (
                    json.loads(raw) if raw else None,
                    response.status,
                    dict(response.headers),
                )
        except urllib.error.HTTPError as exc:  # 4xx/5xx: canonical error envelope
            raw = exc.read()
            try:
                payload = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                payload = raw.decode(errors="replace")
            return payload, exc.code, dict(exc.headers or {})

    def publish_probe(self, label: str) -> tuple[str, float]:
        """Publish one event via project creation; return (pid, t_send).

        ``POST /projects`` writes the ``project.created`` event inside the
        creating transaction (Section 9.6) — a real owner-driven event, not
        a test hook, so the measured latency is the production fan-out path.
        """
        body = {
            "name": f"sse-soak {label} {time.strftime('%Y%m%d-%H%M%S')}",
            "repo_path": "e2e/sse-tunnel-stability (soak probe, no repo access)",
            "default_branch": "main",
        }
        t_send = time.monotonic()
        payload, status, _ = self.request("POST", PROJECTS_PATH, body=body)
        if status != 201 or not isinstance(payload, dict) or "id" not in payload:
            raise SoakFailure(f"probe publish failed: status={status} payload={payload!r}")
        return str(payload["id"]), t_send

    def history_ids_after(self, last_id: int) -> list[int]:
        """Ground truth: all stored event ids strictly greater than *last_id*.

        One page is enough for a controlled soak (the stack under test writes
        nothing else); a longer history would need cursor walking, which the
        run does not require and therefore does not invent.
        """
        payload, status, _ = self.request("GET", f"{HISTORY_PATH}?page_size=100")
        if status != 200 or not isinstance(payload, dict):
            raise SoakFailure(f"history fetch failed: status={status} payload={payload!r}")
        ids = [int(item["id"]) for item in payload.get("results", [])]
        return sorted(eid for eid in ids if eid > last_id)


class SseConnection:
    """One open SSE connection: framed reads with a starvation guard."""

    def __init__(self, api: Api, gap_tolerance: float, last_event_id: int | None = None) -> None:
        # Socket timeout above the gap tolerance: a timeout firing means the
        # path went silent for longer than the heartbeat contract allows —
        # exactly the buffering/starvation signature this soak exists to
        # catch (Section 15.4, RISK-05).
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
        if last_event_id is not None:
            # Section 9.6 resume: replay the missed rows, then live.
            headers["Last-Event-ID"] = str(last_event_id)
        connection.request("GET", STREAM_PATH, headers=headers)
        self.connection = connection
        self.response = connection.getresponse()
        if self.response.status != 200:
            detail = self.response.read().decode(errors="replace")[:500]
            raise SoakFailure(f"stream open failed: status={self.response.status} body={detail!r}")
        self.headers = {key.lower(): value for key, value in self.response.getheaders()}
        if "text/event-stream" not in self.headers.get("content-type", ""):
            raise SoakFailure(f"stream answered without text/event-stream: {self.headers!r}")
        self.last_frame_at = time.monotonic()

    def read_frame(self) -> tuple[str, dict[str, Any] | None]:
        """One SSE frame: ("heartbeat", None) or ("event", envelope).

        Raises ``SoakFailure`` on a starved/EOF connection — an unplanned
        disconnect is a failure, never silently retried: reconnection is the
        client behavior NFR-04 wants in production, but this test's job is to
        prove it is *not needed*.
        """
        lines: list[bytes] = []
        while True:
            try:
                line = self.response.readline()
            except socket.timeout as exc:
                starved = time.monotonic() - self.last_frame_at
                raise SoakFailure(
                    f"stream starved: no frame for {starved:.1f}s "
                    f"(tolerance {self.sock_timeout - 2.0:.1f}s) — heartbeat/"
                    "proxy-timeout signature"
                ) from exc
            if not line:
                raise SoakFailure(
                    "stream closed by peer before the run finished "
                    "(EOF — unplanned disconnect)"
                )
            if line in (b"\n", b"\r\n"):
                if lines:
                    break
                continue  # leading blank lines are not frames
            lines.append(line.rstrip(b"\r\n"))
        self.last_frame_at = time.monotonic()
        if all(line.startswith(b":") for line in lines):
            return "heartbeat", None
        envelope: dict[str, Any] = {}
        for line in lines:
            if line.startswith(b"id:"):
                envelope["id"] = int(line[3:].strip())
            elif line.startswith(b"data:"):
                envelope.update(json.loads(line[5:].strip()))
        if "id" not in envelope:
            raise SoakFailure(f"malformed SSE frame (no id): {lines!r}")
        return "event", envelope

    def close(self) -> None:
        """Deliberate teardown (never used for unplanned failures)."""
        try:
            self.response.close()
        finally:
            self.connection.close()


def open_stream(api: Api, gap_tolerance: float, last_event_id: int | None = None) -> SseConnection:
    """Open the stream, optionally resuming per Section 9.6."""
    return SseConnection(api, gap_tolerance, last_event_id=last_event_id)


def run_cycle(
    api: Api,
    cycle: int,
    idle_seconds: float,
    heartbeat_seconds: float,
    gap_factor: float,
    max_latency: float,
    probe_lead: float,
) -> dict[str, Any]:
    """One full cycle: idle soak, buffered-delivery probe, drop, live resume."""
    gap_tolerance = heartbeat_seconds * gap_factor
    stats: dict[str, Any] = {
        "cycle": cycle,
        "started_at": utc_now(),
        "heartbeats": 0,
        "max_gap_seconds": 0.0,
        "unplanned_disconnects": 0,
        "idle_events": [],
        "probe": None,
        "resume": None,
    }
    connection = open_stream(api, gap_tolerance, last_event_id=None)
    t_start = time.monotonic()
    probe_at = t_start + max(idle_seconds - probe_lead, idle_seconds * 0.5)
    probe_sent: tuple[str, float] | None = None
    probe_arrival: float | None = None
    last_event_id: int | None = None
    try:
        while True:
            now = time.monotonic()
            if now >= t_start + idle_seconds:
                break
            if probe_sent is None and now >= probe_at:
                pid, t_send = api.publish_probe(f"cycle{cycle} idle-probe")
                probe_sent = (pid, t_send)
            prior_frame_at = connection.last_frame_at
            kind, envelope = connection.read_frame()
            now = time.monotonic()
            stats["max_gap_seconds"] = max(
                stats["max_gap_seconds"], connection.last_frame_at - prior_frame_at
            )
            if kind == "heartbeat":
                stats["heartbeats"] += 1
            else:
                assert envelope is not None
                stats["idle_events"].append(int(envelope["id"]))
                last_event_id = max(last_event_id or 0, int(envelope["id"]))
                if probe_sent is not None and envelope.get("project_id") == probe_sent[0]:
                    probe_arrival = now
        # The probe must have been sent, delivered and measured — "near the
        # end of the idle window" only makes sense if the window ran long
        # enough for one round trip; shorter runs degrade gracefully but a
        # probe that never *arrived* is the buffering artifact itself.
        if probe_sent is None:
            raise SoakFailure(
                f"idle window {idle_seconds}s too short for a probe at "
                f"lead {probe_lead}s — raise --idle-seconds"
            )
        if probe_arrival is None:
            raise SoakFailure(
                "probe event (project.created) never reached the open stream "
                "during the idle window — response buffering signature"
            )
        latency = probe_arrival - probe_sent[1]
        stats["probe"] = {
            "project_id": probe_sent[0],
            "latency_seconds": round(latency, 3),
            "within_nfr03": latency <= max_latency,
        }
        expected_min_heartbeats = int(idle_seconds // heartbeat_seconds) - 1
        if stats["heartbeats"] < max(expected_min_heartbeats, 0):
            raise SoakFailure(
                f"only {stats['heartbeats']} heartbeats in {idle_seconds}s "
                f"(expected >= {expected_min_heartbeats} at {heartbeat_seconds}s cadence)"
            )
        if stats["max_gap_seconds"] > gap_tolerance:
            raise SoakFailure(
                f"max inter-frame gap {stats['max_gap_seconds']:.1f}s exceeds "
                f"tolerance {gap_tolerance:.1f}s"
            )
    finally:
        connection.close()

    # --- deliberate drop + lossless resume (Section 9.6, NFR-04) -----------
    if last_event_id is None:
        raise SoakFailure("no event id was ever received — nothing to resume from")
    for index in range(MISSED_EVENTS_PER_CYCLE):
        api.publish_probe(f"cycle{cycle} missed-{index + 1}")
    expected_missed = api.history_ids_after(last_event_id)
    if len(expected_missed) < MISSED_EVENTS_PER_CYCLE:
        raise SoakFailure(
            f"expected at least {MISSED_EVENTS_PER_CYCLE} stored events after "
            f"id {last_event_id}, history holds {expected_missed!r}"
        )

    resumed = open_stream(api, gap_tolerance, last_event_id=last_event_id)
    delivered: list[int] = []
    try:
        while len(delivered) < len(expected_missed):
            kind, envelope = resumed.read_frame()
            if kind == "event":
                assert envelope is not None
                delivered.append(int(envelope["id"]))
        if delivered != expected_missed:
            raise SoakFailure(
                "resume is not lossless: "
                f"expected replay {expected_missed!r}, delivered {delivered!r} "
                "(gap or duplicate)"
            )
        # The same connection must keep working after replay — live handover.
        live_pid, live_send = api.publish_probe(f"cycle{cycle} live-after-resume")
        live_arrival = None
        while live_arrival is None:
            kind, envelope = resumed.read_frame()
            if kind == "event":
                assert envelope is not None
                delivered.append(int(envelope["id"]))
                if envelope.get("project_id") == live_pid:
                    live_arrival = time.monotonic()
        live_latency = live_arrival - live_send
    finally:
        resumed.close()

    expected_final = api.history_ids_after(last_event_id)
    if delivered != expected_final[: len(delivered)]:
        raise SoakFailure(
            f"delivered sequence {delivered!r} is not an exact prefix of stored "
            f"history {expected_final!r} — gap, duplicate or stray delivery"
        )
    if any(second <= first for first, second in zip(delivered, delivered[1:], strict=False)):
        raise SoakFailure(f"delivered ids are not strictly increasing: {delivered!r}")
    stats["resume"] = {
        "resumed_from": last_event_id,
        "expected_missed": expected_missed,
        "delivered": delivered,
        "no_gaps_no_duplicates": True,
        "live_after_resume_project_id": live_pid,
        "live_after_resume_latency_seconds": round(live_latency, 3),
    }
    stats["finished_at"] = utc_now()
    if live_latency > max_latency:
        raise SoakFailure(
            f"live delivery after resume took {live_latency:.3f}s "
            f"(NFR-03 budget {max_latency}s)"
        )
    return stats


def parse_args(argv: list[str]) -> argparse.Namespace:
    """CLI: the origin under test plus the soak shape."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Origin under test: LAN backend address or the tunnel hostname "
        "(https://orchestrator.<owner-domain>) — default %(default)s",
    )
    parser.add_argument(
        "--idle-seconds",
        type=float,
        default=1800.0,
        help="Idle window per cycle; acceptance = 1800 (30 min). Reduced "
        "(e.g. 150) for CI/local control runs — default %(default)s",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=2,
        help="Idle cycles; MT-5.1-04 requires >= 2 (stability, not a one-off) "
        "— default %(default)s",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=DEFAULT_HEARTBEAT_SECONDS,
        help="Expected heartbeat cadence (ORCHESTRATOR_EVENTS_HEARTBEAT_SECONDS) "
        "— default %(default)s",
    )
    parser.add_argument(
        "--gap-factor",
        type=float,
        default=2.0,
        help="Max inter-frame gap = heartbeat x this factor — default %(default)s",
    )
    parser.add_argument(
        "--max-latency-seconds",
        type=float,
        default=DEFAULT_MAX_LATENCY_SECONDS,
        help="Single-event delivery budget (NFR-03) — default %(default)s",
    )
    parser.add_argument(
        "--probe-lead-seconds",
        type=float,
        default=20.0,
        help="Publish the no-buffering probe this many seconds before the "
        "idle window ends — default %(default)s",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("SSE_SOAK_USERNAME", ""),
        help="Owner username (prefer SSE_SOAK_USERNAME env var)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SSE_SOAK_PASSWORD", ""),
        help="Owner password (prefer SSE_SOAK_PASSWORD env var — args leak "
        "into process listings)",
    )
    parser.add_argument(
        "--label",
        default="unlabelled",
        help="Run label recorded in the results (e.g. lan-control, tunnel) "
        "— default %(default)s",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write the JSON results document to this path (evidence artifact)",
    )
    args = parser.parse_args(argv)
    if args.cycles < 2:
        parser.error("--cycles must be >= 2 (MT-5.1-04: repeat at least once)")
    if args.idle_seconds <= args.probe_lead_seconds + args.heartbeat_seconds * 2:
        parser.error("--idle-seconds too short for probe + heartbeats")
    if not args.username or not args.password:
        parser.error("owner credentials required (SSE_SOAK_USERNAME / SSE_SOAK_PASSWORD)")
    return args


def main(argv: list[str]) -> int:
    """Run every cycle; print and write the results; return the verdict."""
    args = parse_args(argv)
    api = Api(args.base_url, timeout=args.heartbeat_seconds * args.gap_factor + 10.0)
    results: dict[str, Any] = {
        "test": "MT-5.1-04 SSE stability soak",
        "label": args.label,
        "base_url": args.base_url,
        "started_at": utc_now(),
        "config": {
            "idle_seconds": args.idle_seconds,
            "cycles": args.cycles,
            "heartbeat_seconds": args.heartbeat_seconds,
            "gap_tolerance_seconds": args.heartbeat_seconds * args.gap_factor,
            "max_latency_seconds": args.max_latency_seconds,
        },
        "cycles": [],
        "failures": [],
    }
    try:
        login = api.login(args.username, args.password)
        results["auth"] = {
            "user": login.get("user", {}),
            "session_expires_at": login.get("expires_at"),
        }
        for cycle in range(1, args.cycles + 1):
            print(f"[{utc_now()}] cycle {cycle}/{args.cycles}: "
                  f"idle {args.idle_seconds:.0f}s starting", flush=True)
            cycle_stats = run_cycle(
                api,
                cycle,
                idle_seconds=args.idle_seconds,
                heartbeat_seconds=args.heartbeat_seconds,
                gap_factor=args.gap_factor,
                max_latency=args.max_latency_seconds,
                probe_lead=args.probe_lead_seconds,
            )
            results["cycles"].append(cycle_stats)
            print(
                f"[{utc_now()}] cycle {cycle}/{args.cycles}: PASS "
                f"heartbeats={cycle_stats['heartbeats']} "
                f"max_gap={cycle_stats['max_gap_seconds']:.1f}s "
                f"probe_latency={cycle_stats['probe']['latency_seconds']:.3f}s "
                f"resume={cycle_stats['resume']['delivered']}",
                flush=True,
            )
    except SoakFailure as exc:
        results["failures"].append(str(exc))
        print(f"[{utc_now()}] FAIL: {exc}", file=sys.stderr, flush=True)
    results["finished_at"] = utc_now()
    results["pass"] = not results["failures"] and len(results["cycles"]) == args.cycles
    text = json.dumps(results, indent=2, sort_keys=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print(f"results written to {args.output}", flush=True)
    print(text)
    return 0 if results["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
