"""WP-6.3 — measurement hygiene: release simulation-held leases between runs.

Each simulation run leaves its in-flight claims held at the deadline
(agents stopped mid-cycle with a live lease). Stacked runs would eat the
project's ``max_concurrent_tasks`` headroom (G-26), so later runs would
see a *different* offer/concurrency mix than earlier ones. This harness
resets that fixture state through the **real owner release endpoint**
between scenario runs, giving every recorded run the same starting
conditions (MT-6.3-02 run-count discipline; a fixture-state reset, never
a product change).

Only leases held by the seed manifest's ``perf-agent-*`` sessions are
released — the four seeded dormant ``in_progress`` holds per project stay
untouched (they are part of the fixture's state distribution).

Run: ``python e2e/perf/release_held_leases.py`` (stack must be up, seed
applied). Prints released/failed counts; exit 2 on auth/stack problems.
"""

from __future__ import annotations

import os
import sys

from perf_common import Api, PerfError, load_manifest
from seed_perf_fixture import DEFAULT_OWNER_PASSWORD

HOLD_PREFIX = "perf-agent-"
RELEASE_REASON = (
    "WP-6.3 measurement hygiene: owner release of simulation-held lease "
    "between recorded runs (MT-6.3-02 run-count discipline)"
)


def main() -> int:
    manifest = load_manifest()
    owner = Api()
    try:
        owner.login(
            manifest["owner"]["username"],
            os.environ.get("PERF_OWNER_PASSWORD", DEFAULT_OWNER_PASSWORD),
        )
    except PerfError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    released = 0
    failed: list[tuple[str, int]] = []
    for pid in manifest["projects"]:
        cursor: str | None = None
        while True:
            path = f"/projects/{pid}/tasks?state=in_progress&page_size=100"
            if cursor:
                path += f"&cursor={cursor}"
            payload, status, _ = owner.request("GET", path)
            if status != 200 or not isinstance(payload, dict):
                raise PerfError(f"task list failed for {pid}: status={status}")
            for row in payload["results"]:
                session = row.get("worker_session_id") or ""
                if not session.startswith(HOLD_PREFIX):
                    continue  # seeded dormant holds stay (fixture state)
                _, r_status, _ = owner.request(
                    "POST",
                    f"/tasks/{row['id']}/release",
                    body={"reason": RELEASE_REASON},
                )
                if r_status == 200:
                    released += 1
                else:
                    failed.append((str(row["id"]), r_status))
            cursor = payload.get("next_cursor")
            if not cursor:
                break

    print(f"released={released} failed={len(failed)}")
    for task_id, status in failed[:10]:
        print(f"  {task_id}: HTTP {status}")
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
