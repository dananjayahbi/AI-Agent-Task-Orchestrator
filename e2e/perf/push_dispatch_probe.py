"""MT-6.3-01 — sender-side dispatch probe (NFR-03's 10 s push half, partial).

**Method statement (carried into MT-6.3-02's report):**
the probe clocks a *host wall clock* from the moment an escalating
resolution POST is sent to the first ``dispatch_push`` line the Celery
worker logs (``docker compose logs worker --timestamps``). The
transaction's ``transaction.on_commit`` enqueue runs inside that request
before the response returns, so trigger <= enqueue <= job execution —
the measured span is a conservative upper bound of backend-trigger ->
dispatch-job-run. A ``succeeded in`` line for the same Celery task id,
when present, is recorded as job completion.

**What this does NOT claim:** device delivery through FCM. The stack runs
with **zero registered devices** (no ``Device`` rows): the dispatch job's
fan-out loop finds no recipients and completes without contacting
Google. The device leg is owned by MT-5.10-05 / WP-5.4 and is
cross-referenced here, never proven here (MT-6.3-01/02 risk notes).

Trigger path exercised: claim -> submit ``requires_human_attention=true``
-> T8 ``in_human_review`` -> ``trigger_review_push`` ->
``dispatch_push_task.delay`` — wired only when the stack runs with
``ORCHESTRATOR_PUSH_ENABLED=true`` (``e2e/perf/stack.py`` sets it; the
wellformed fixture credentials never leave the host — zero devices means
the transport is never built).

Run: ``python e2e/perf/push_dispatch_probe.py --triggers 10 --run-id 1``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from perf_common import (
    Api,
    PerfError,
    compose_argv,
    judge,
    load_manifest,
    load_thresholds,
    summarize,
    verdict_line,
    write_results,
)

DISPATCH_MARK = "dispatch_push"
UUID_IN_LINE = re.compile(r"dispatch_push\[([0-9a-f-]{36})\]")
# compose logs --timestamps prefixes the line with the service column:
#   worker-1  | 2026-10-15T11:57:35.288858516Z [2026-10-15 ...] Task ...
ISO_TIMESTAMP = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)")
POLL_INTERVAL_S = 0.5
TRIGGER_TIMEOUT_S = 15.0


def parse_docker_timestamp(token: str) -> datetime | None:
    """Parse docker's RFC3339 nano timestamp (truncate to microseconds)."""
    try:
        head, _, fraction = token.partition(".")
        if fraction:
            digits = fraction.rstrip("Z")
            token = f"{head}.{digits[:6].ljust(6, '0')}+00:00"
        else:
            token = f"{token}+00:00" if not token.endswith("Z") else token.replace("Z", "+00:00")
        return datetime.fromisoformat(token)
    except ValueError:
        return None


def scan_worker_log(since: datetime) -> list[tuple[datetime, str]]:
    """``(timestamp, message)`` worker log lines at/after *since*."""
    since_text = since.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    completed = subprocess.run(
        compose_argv("logs", "worker", "--timestamps", "--since", since_text),
        capture_output=True,
    )
    if completed.returncode != 0:
        raise PerfError(
            "docker compose logs worker failed — perf stack up? "
            f"({completed.stderr.decode(errors='replace').strip()})"
        )
    rows: list[tuple[datetime, str]] = []
    for line in completed.stdout.decode(errors="replace").splitlines():
        match = ISO_TIMESTAMP.search(line)
        if match is None:
            continue
        stamp = parse_docker_timestamp(match.group(1))
        if stamp is None or stamp < since:
            continue
        rows.append((stamp, line))
    return rows


def probe_one(api: Api, agent: dict[str, Any], index: int) -> dict[str, Any]:
    """Claim one task, escalate it, and time the worker's dispatch job."""
    pid = agent["project_id"]
    work, status, _ = api.request(
        "GET", f"/projects/{pid}/work?role=coder&page_size=10", token=agent["token"]
    )
    if status != 200 or not isinstance(work, dict) or not work.get("results"):
        return {"index": index, "ok": False, "reason": f"no work: status={status}"}

    for row in work["results"]:
        task_id = str(row["id"])
        claim, status, _ = api.request(
            "POST",
            f"/tasks/{task_id}/claim",
            body={
                "session_id": agent["session_id"],
                "worker_agent_id": agent["worker_agent_id"],
                "role": "coder",
            },
            token=agent["token"],
        )
        if status not in (200, 201) or not isinstance(claim, dict):
            continue  # conflict on this offer: try the next
        lease_generation = int(claim["lease"]["lease_generation"])

        trigger_at = datetime.now(UTC)
        resolution, status, _ = api.request(
            "POST",
            f"/tasks/{task_id}/resolution",
            body={
                "session_id": agent["session_id"],
                "lease_generation": lease_generation,
                "git_branch": f"perf/{pid}",
                "commit_sha": "0000000000000000000000000000000000000000",  # pragma: allowlist secret
                "execution_summary": "WP-6.3 sender-side dispatch probe (MT-6.3-01).",
                "requires_human_attention": True,
                "risk_justification": "WP-6.3 push-dispatch measurement escalation.",
                "patch": "",
            },
            token=agent["token"],
        )
        if status not in (200, 201) or not isinstance(resolution, dict):
            return {
                "index": index,
                "task_id": task_id,
                "ok": False,
                "reason": f"escalation submit failed: status={status}",
            }

        # Poll the worker log for this trigger's dispatch job.
        deadline = time.monotonic() + TRIGGER_TIMEOUT_S
        grace_deadline: float | None = None
        received_ms: float | None = None
        completed_ms: float | None = None
        task_uuid: str | None = None
        while time.monotonic() < deadline:
            rows = scan_worker_log(trigger_at - timedelta(seconds=2))
            for stamp, message in rows:
                if DISPATCH_MARK not in message or stamp < trigger_at:
                    continue
                match = UUID_IN_LINE.search(message)
                if match:
                    task_uuid = match.group(1)
                if received_ms is None:
                    received_ms = (stamp - trigger_at).total_seconds() * 1000.0
                if task_uuid and task_uuid in message and "succeeded in" in message:
                    completed_ms = (stamp - trigger_at).total_seconds() * 1000.0
            if completed_ms is not None:
                break
            if received_ms is not None:
                # Job picked up: give completion a short grace, then accept
                # "received" as the observable end (recorded, not hidden).
                if grace_deadline is None:
                    grace_deadline = time.monotonic() + 3.0
                elif time.monotonic() >= grace_deadline:
                    break
            time.sleep(POLL_INTERVAL_S)
        return {
            "index": index,
            "task_id": task_id,
            "ok": True,
            "received_ms": round(received_ms, 2) if received_ms is not None else None,
            "completed_ms": round(completed_ms, 2) if completed_ms is not None else None,
            "celery_task_uuid": task_uuid,
            "clock": "host wall clock -> docker log timestamp (same host, UTC)",
        }
    return {"index": index, "ok": False, "reason": "every claim attempt conflicted"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    thresholds = load_thresholds()
    parser = argparse.ArgumentParser(
        description="WP-6.3 push-dispatch probe — backend->sender leg (MT-6.3-01)."
    )
    parser.add_argument("--triggers", type=int, default=10)
    parser.add_argument("--run-id", type=int, default=1)
    parser.add_argument("--manifest", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = load_manifest(args.manifest)
    thresholds = load_thresholds()
    budget_ms = thresholds["nfr03"]["push_dispatch_ms"]

    api = Api()
    attempts: list[dict[str, Any]] = []
    for index in range(args.triggers):
        agent = manifest["agents"][index % len(manifest["agents"])]
        attempts.append(probe_one(api, agent, index))

    timed = [a for a in attempts if a.get("ok") and a.get("completed_ms") is not None]
    clock_key = "completed_ms"
    if not timed:
        timed = [a for a in attempts if a.get("ok") and a.get("received_ms") is not None]
        clock_key = "received_ms"
    values = [float(a[clock_key]) for a in timed]
    stats = summarize(values)

    if values:
        verdict = judge(stats["p95_ms"], budget_ms)
        verdict.update(
            {
                "measured": True,
                "clock": clock_key,
                "label": "backend-trigger -> dispatch-job completion (zero devices; FCM never contacted)",
            }
        )
        verdict_line_text = verdict_line("nfr03_push_dispatch (backend->sender leg)", verdict)
    else:
        verdict = {
            "budget_ms": budget_ms,
            "p95_ms": None,
            "pass": False,
            "measured": False,
            "reason": (
                "no dispatch_push lines in the worker log — push wiring absent "
                "(ORCHESTRATOR_PUSH_ENABLED not applied to the running stack?) "
                "or the hook did not fire; nothing was measured, nothing is claimed"
            ),
        }
        verdict_line_text = "NOT-MEASURED nfr03_push_dispatch: no dispatch job observed"

    payload: dict[str, Any] = {
        "run_id": args.run_id,
        "triggers_requested": args.triggers,
        "triggers_ok": sum(1 for a in attempts if a.get("ok")),
        "triggers_timed": len(values),
        "method": (
            "host wall clock at escalation-POST send -> worker log timestamp "
            "of the dispatch_push line (on_commit enqueue happens inside the "
            "request, so the span is an upper bound of backend->sender "
            "dispatch); zero registered devices, so the FCM transport is "
            "never built and the device leg stays with MT-5.10-05 / WP-5.4"
        ),
        "latency_ms": stats,
        "verdicts": {"nfr03_push_dispatch_backend_leg": verdict},
        "thresholds_source": "e2e/perf/thresholds.json (plan-derived, Section 5.2)",
        "attempts": attempts,
    }
    path = write_results(f"push_dispatch_probe_run{args.run_id}", payload)
    print(
        f"push_dispatch_probe run={args.run_id} ok={payload['triggers_ok']}/"
        f"{args.triggers} timed={len(values)}"
    )
    print(verdict_line_text)
    print(f"results: {path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PerfError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
