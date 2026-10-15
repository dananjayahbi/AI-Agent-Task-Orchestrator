"""MT-6.3-01 — Agent simulation: 20 concurrent Section 11.1 coder flows.

Scenario shape (Section 18 Performance row): 20 simulated agents cycling
orient -> claim -> checkpoint every 30 s -> submit against the seeded
10,000-task database, measuring per-call latency for claim and checkpoint
— the NFR-02 clocks — with p50/p95/p99 persisted per run.

Scope statement (MT-6.3-01 risk note): this is an **API-level**
simulation of the coder flow (real HTTP endpoints), *not* 20 MCP
bridges — bridge overhead sits outside this scenario, so numbers compare
against the API baseline, not bridge-inclusive ones.

Thresholds: ``e2e/perf/thresholds.json`` (plan-derived constants from
Section 5.2; never edited to make a run pass). Results: one JSON file
per run in ``e2e/perf/results/`` plus a printed PASS/FAIL line per
budget. Execution instructions: ``docs/plan/perf-runbook.md``.

Run: ``python e2e/perf/agent_simulation.py --run-id 1``
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from typing import Any

from perf_common import (
    Api,
    PerfError,
    judge,
    load_manifest,
    load_thresholds,
    summarize,
    verdict_line,
    write_results,
)

# Section 10.5 contracts (verified against the serializers): claim takes
# the fencing identity pair + label; checkpoint adds lease_generation;
# resolution takes the full submission body. Blank patch -> zero changed
# files -> in-scope verdict (seed sets target_scope=["src/**"]).
COMMIT_SHA = "0000000000000000000000000000000000000000"  # pragma: allowlist secret

ABORT_STATUSES = {401, 403}  # token/scope problems are bugs, not load data
CONFLICT_STATUSES = {409}  # duplicate claims / lost races = expected under load


class SampleSink:
    """Thread-safe collector for one run's per-call samples."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.samples: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []

    def add(
        self,
        op: str,
        ms: float,
        status: int,
        agent: int,
        ok: bool,
        detail: str = "",
    ) -> None:
        with self._lock:
            self.samples.append(
                {"op": op, "ms": round(ms, 2), "status": status, "agent": agent, "ok": ok}
            )
            if not ok and status not in CONFLICT_STATUSES and len(self.errors) < 100:
                self.errors.append(
                    {"op": op, "status": status, "agent": agent, "detail": detail[:300]}
                )

    def by_op(self, op: str, ok_only: bool = True) -> list[float]:
        with self._lock:
            return [
                row["ms"]
                for row in self.samples
                if row["op"] == op and (row["ok"] or not ok_only)
            ]

    def count(self, op: str, ok_only: bool = True) -> int:
        return len(self.by_op(op, ok_only=ok_only))


class AgentWorker(threading.Thread):
    """One simulated agent: the Section 11.1 coder loop until the deadline."""

    def __init__(
        self,
        agent: dict[str, Any],
        sink: SampleSink,
        deadline_at: float,
        start_event: threading.Event,
        stop_event: threading.Event,
        checkpoint_interval: float,
        checkpoints_per_task: int,
        registry: Any | None = None,
    ) -> None:
        super().__init__(name=f"agent-{agent['index']}", daemon=True)
        self.agent = agent
        self.sink = sink
        self.deadline_at = deadline_at
        self.start_event = start_event
        self.stop_event = stop_event
        self.checkpoint_interval = checkpoint_interval
        self.checkpoints_per_task = checkpoints_per_task
        self.registry = registry
        self.api = Api(token=agent["token"])
        self.conflicts = 0
        self.rate_limit_hits = 0
        self.tasks_cycled = 0

    def run(self) -> None:
        self.start_event.wait()
        while time.perf_counter() < self.deadline_at and not self.stop_event.is_set():
            if not self._cycle():
                break

    def _aborted(self, status: int) -> bool:
        return status in ABORT_STATUSES

    def _cycle(self) -> bool:
        """One full coder cycle; False stops this agent for good."""
        pid = self.agent["project_id"]
        work, status, ms = self.api.request(
            "GET", f"/projects/{pid}/work?role=coder&page_size=25"
        )
        self.sink.add("orient", ms, status, self.agent["index"], status == 200)
        if self._aborted(status):
            return False
        if status != 200 or not isinstance(work, dict):
            self.stop_event.wait(2.0)
            return True
        rows = work.get("results") or []
        if not rows:
            self.stop_event.wait(2.0)
            return True

        for row in rows:
            if time.perf_counter() >= self.deadline_at or self.stop_event.is_set():
                return False
            task_id = str(row["id"])
            if not self._claim_and_finish(task_id):
                continue  # conflict on this task: try the next offer
            return True
        # Every offer conflicted (or the agent aborted): back off briefly.
        self.stop_event.wait(1.0)
        return True

    def _claim_and_finish(self, task_id: str) -> bool:
        agent_index = self.agent["index"]
        claim, status, ms = self.api.request(
            "POST",
            f"/tasks/{task_id}/claim",
            body={
                "session_id": self.agent["session_id"],
                "worker_agent_id": self.agent["worker_agent_id"],
                "role": "coder",
            },
        )
        self.sink.add("claim", ms, status, agent_index, status in (200, 201))
        if self._aborted(status):
            self.stop_event.set()  # token is bad: stop the whole run loudly
            return False
        if status in CONFLICT_STATUSES:
            self.conflicts += 1
            return False
        if status == 429:
            self.rate_limit_hits += 1
            self.stop_event.wait(5.0)
            return False
        if status not in (200, 201) or not isinstance(claim, dict):
            return False
        try:
            lease_generation = int(claim["lease"]["lease_generation"])
        except (KeyError, TypeError, ValueError):
            self.sink.add("claim", ms, status, agent_index, False, "malformed lease")
            return False

        for index in range(self.checkpoints_per_task):
            if index > 0:
                if self.stop_event.wait(self.checkpoint_interval):
                    return False
                if time.perf_counter() >= self.deadline_at:
                    return False
            handle = self.registry.begin(agent_index) if self.registry else None
            t_send = time.perf_counter() if self.registry else None
            payload, status, ms = self.api.request(
                "POST",
                f"/tasks/{task_id}/checkpoints",
                body={
                    "session_id": self.agent["session_id"],
                    "lease_generation": lease_generation,
                    "message": f"perf checkpoint {index + 1}/{self.checkpoints_per_task}",
                    "kind": "progress",
                },
            )
            t_resp = time.perf_counter()
            ok = status in (200, 201) and isinstance(payload, dict)
            self.sink.add("checkpoint", ms, status, agent_index, ok)
            if self.registry and ok:
                checkpoint_id = str(payload["checkpoint"]["id"])
                self.registry.finish(agent_index, handle, checkpoint_id, t_send, t_resp)
            if self._aborted(status):
                self.stop_event.set()
                return False
            if not ok:
                return False  # lease lost mid-hold: this task is done for us

        resolution, status, ms = self.api.request(
            "POST",
            f"/tasks/{task_id}/resolution",
            body={
                "session_id": self.agent["session_id"],
                "lease_generation": lease_generation,
                "git_branch": f"perf/{self.agent['project_id']}",
                "commit_sha": COMMIT_SHA,
                "execution_summary": "WP-6.3 perf simulation submit (MT-6.3-01).",
                "requires_human_attention": False,
                "risk_justification": "",
                "patch": "",
            },
        )
        submitted = status in (200, 201)
        self.sink.add("submit", ms, status, agent_index, submitted)
        if self._aborted(status):
            self.stop_event.set()
            return False
        if submitted:
            self.tasks_cycled += 1
            return True
        return False


def start_simulation(
    args: argparse.Namespace,
    registry: Any | None = None,
    stop_event: threading.Event | None = None,
    start_event: threading.Event | None = None,
    deadline_at: float | None = None,
) -> tuple[dict[str, Any], dict[str, Any], SampleSink, list[AgentWorker]]:
    """Start the worker threads; return ``(manifest, thresholds, sink, workers)``.

    The caller owns joining: the results payload must only be assembled via
    :func:`build_payload` **after** every worker has finished, or it snapshots
    zeros (the mistake this split exists to prevent).
    """
    manifest = load_manifest(getattr(args, "manifest", None))
    thresholds = load_thresholds()
    agents = manifest["agents"][: args.agents]
    if len(agents) < args.agents:
        raise PerfError(
            f"manifest holds {len(manifest['agents'])} agents, requested {args.agents} — re-seed"
        )

    sink = SampleSink()
    stop = stop_event or threading.Event()
    start = start_event or threading.Event()
    wall_begin = time.perf_counter()
    end_at = deadline_at if deadline_at is not None else wall_begin + args.duration
    workers = [
        AgentWorker(
            agent=agent,
            sink=sink,
            deadline_at=end_at,
            start_event=start,
            stop_event=stop,
            checkpoint_interval=args.checkpoint_interval,
            checkpoints_per_task=args.checkpoints_per_task,
            registry=registry,
        )
        for agent in agents
    ]
    for worker in workers:
        worker.start()
    start.set()
    return manifest, thresholds, sink, workers


def build_payload(
    args: argparse.Namespace,
    manifest: dict[str, Any],
    thresholds: dict[str, Any],
    sink: SampleSink,
    workers: list[AgentWorker],
) -> dict[str, Any]:
    """Assemble the run's results — call only after all workers joined."""
    agents = manifest["agents"][: args.agents]
    claim_ms = sink.by_op("claim")
    checkpoint_ms = sink.by_op("checkpoint")
    nfr02 = thresholds["nfr02"]
    verdicts = {
        "nfr02_claim_p95": judge(summarize(claim_ms)["p95_ms"], nfr02["claim_p95_ms"]),
        "nfr02_checkpoint_p95": judge(
            summarize(checkpoint_ms)["p95_ms"], nfr02["checkpoint_p95_ms"]
        ),
    }
    payload: dict[str, Any] = {
        "run_id": getattr(args, "run_id", None),
        "duration_s": args.duration,
        "agents_requested": args.agents,
        "agents_started": len(workers),
        "checkpoint_interval_s": args.checkpoint_interval,
        "checkpoints_per_task": args.checkpoints_per_task,
        "seed": manifest["seed"],
        "nfr09_shape": {
            "projects": len({agent["project_id"] for agent in agents}),
            "concurrent_sessions": len(agents),
            "tasks": manifest["counts"]["tasks"],
            "attachment_gb": thresholds["nfr09"]["attachment_gb"],
        },
        "counts": {
            "orient_ok": sink.count("orient"),
            "claim_ok": sink.count("claim"),
            "claim_conflicts": sum(w.conflicts for w in workers),
            "rate_limit_hits": sum(w.rate_limit_hits for w in workers),
            "checkpoint_ok": sink.count("checkpoint"),
            "submit_ok": sink.count("submit"),
            "tasks_cycled": sum(w.tasks_cycled for w in workers),
            "http_errors": len(sink.errors),
        },
        "latency_ms": {
            "claim": summarize(claim_ms),
            "checkpoint": summarize(checkpoint_ms),
            "orient": summarize(sink.by_op("orient")),
            "submit": summarize(sink.by_op("submit")),
        },
        "verdicts": verdicts,
        "thresholds_source": "e2e/perf/thresholds.json (plan-derived, Section 5.2)",
        "errors": sink.errors,
        "workers": [
            {
                "agent": w.agent["index"],
                "project_id": w.agent["project_id"],
                "conflicts": w.conflicts,
                "tasks_cycled": w.tasks_cycled,
            }
            for w in workers
        ],
    }
    return payload


def run_simulation(
    args: argparse.Namespace,
    registry: Any | None = None,
    stop_event: threading.Event | None = None,
    start_event: threading.Event | None = None,
    deadline_at: float | None = None,
) -> tuple[dict[str, Any], list[AgentWorker]]:
    """Standalone convenience: start the load, join every worker, build.

    ``sse_fanout`` does its own start/join/build around
    :func:`start_simulation` + :func:`build_payload` so its payload is
    assembled after the workers finish.
    """
    manifest, thresholds, sink, workers = start_simulation(
        args,
        registry=registry,
        stop_event=stop_event,
        start_event=start_event,
        deadline_at=deadline_at,
    )
    end_at = workers[0].deadline_at if workers else time.perf_counter()
    for worker in workers:
        worker.join(timeout=max(0.0, end_at - time.perf_counter()) + 120.0)
    return build_payload(args, manifest, thresholds, sink, workers), workers


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    thresholds = load_thresholds()
    parser = argparse.ArgumentParser(
        description="WP-6.3 agent simulation — 20 coder flows, NFR-02 clocks (MT-6.3-01)."
    )
    parser.add_argument("--run-id", type=int, default=1)
    parser.add_argument("--duration", type=float, default=150.0, help="seconds of load")
    parser.add_argument("--agents", type=int, default=thresholds["scenario"]["agents"])
    parser.add_argument(
        "--checkpoint-interval",
        type=float,
        default=float(thresholds["scenario"]["checkpoint_interval_s"]),
    )
    parser.add_argument("--checkpoints-per-task", type=int, default=3)
    parser.add_argument("--manifest", default=None, help="path to the seed manifest")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload, _workers = run_simulation(args)
    path = write_results(f"agent_simulation_run{args.run_id}", payload)
    counts = payload["counts"]
    print(
        f"agent_simulation run={args.run_id} duration={args.duration}s "
        f"claims_ok={counts['claim_ok']} checkpoints_ok={counts['checkpoint_ok']} "
        f"submits_ok={counts['submit_ok']} conflicts={counts['claim_conflicts']} "
        f"http_errors={counts['http_errors']}"
    )
    for label, verdict in payload["verdicts"].items():
        print(verdict_line(label, verdict))
    print(f"results: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
