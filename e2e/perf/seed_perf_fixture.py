"""MT-6.3-01 — deterministic NFR-09 seed: 10 projects / 10,000 tasks / 20 sessions.

One file, two modes:

* **host mode** (default): ``python e2e/perf/seed_perf_fixture.py`` — copies
  this file into the perf stack's ``backend`` container and runs it there
  with the Django environment already configured (Section 16.1 production
  topology, prod settings module), then writes the run manifest (owner +
  per-agent tokens) to ``e2e/perf/.run/manifest.json`` — gitignored,
  because the agent tokens are live plaintext credentials for the run.
* **inner mode** (``PERF_SEED_INNER=1``, set by the host wrapper): performs
  the seed inside the container via ORM calls and prints a single-line
  JSON manifest on stdout.

Fixture decisions (documented for MT-6.3-02's report; all plan-cited):

* Documented RNG seed ``6301`` (``PERF_SEED`` overrides) — the fixture is
  reproducible by re-running against a fresh stack.
* 10 projects through ``create_project`` (the Section 7.1 policy+project
  pair), then ``agent_policy.max_concurrent_tasks`` raised from the G-26
  default of 1 to 10 (the value backend tests use) so two live coders per
  project never queue behind the seeded ``in_progress`` holds.
* 1,000 tasks per project = 10,000 (NFR-09), ids ``PID0000N-T001..T1000``
  (Section 7.3 shape). ``project.task_counter`` is set to the seeded count
  so a later API-created task continues at ``T1001`` — the allocator stays
  the only writer during the run.
* State spread across the six canonical states (G-01), per 1,000:
  100 completed, 60 in_human_review, 90 to_be_audited, 4 in_progress
  (future leases, no sweeper churn), 40 draft, 150 pending *blocked* on a
  pending/draft dependency chain (never offered by the work list), 556
  pending free — the pool the simulation claims from.
* ``target_scope=["src/**"]`` and ``audit_required=True`` on every task:
  the simulation submits a blank patch (zero changed files -> in-scope
  verdict, Section 12.3) with audit on, so submits land deterministically
  in ``to_be_audited`` (T13) instead of the policy engine's escalations.
* 20 agent tokens + sessions, agent ``i`` -> project ``i % 10`` (two
  concurrent sessions per project), scopes ``["coder"]``, capability
  ``text_only``, transport ``http`` — API-level simulation of the Section
  11.1 flow, not MCP bridges (MT-6.3-01 risk note).

Run cost: bulk inserts of ~11.5k rows, seconds on the local stack; cleanup
is stack teardown (``python e2e/perf/stack.py down -v``), documented in
``docs/plan/perf-runbook.md``. One seed serves every scenario run —
documented procedure instead of per-run reseeding (MT-6.3-01 risk note).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

FIXTURE_SEED = 6301
AGENT_COUNT = 20
PROJECT_COUNT = 10
TASKS_PER_PROJECT = 1000
DEFAULT_OWNER_USERNAME = "perf-owner"
DEFAULT_OWNER_PASSWORD = "wp63-fixture-owner-pass"  # pragma: allowlist secret
SEED_MARKER = "perf-seed"

# Per-1,000 state plan (order defines id ranges; sums to 1,000).
# (state, count) — chain layout below assigns them to contiguous id ranges.
STATE_PLAN: tuple[tuple[str, int], ...] = (
    ("completed", 100),  # T001..T100 — dependency anchors (already done)
    ("in_human_review", 60),  # T101..T160
    ("to_be_audited", 90),  # T161..T250
    ("in_progress", 4),  # T251..T254 — future leases, dormant holds
    ("draft", 40),  # T255..T294 — the blocked chain's tail anchor
    ("pending_blocked", 150),  # T295..T444 — pending, deps incomplete
    ("pending_free", 556),  # T445..T1000 — the claimable pool
)
PRIORITY_WEIGHTS = (("medium", 0.60), ("high", 0.20), ("low", 0.15), ("urgent", 0.05))


def _state_ranges() -> list[tuple[str, int, int]]:
    """``(state, first_n, last_n)`` id ranges from the plan above."""
    ranges: list[tuple[str, int, int]] = []
    cursor = 1
    for state, count in STATE_PLAN:
        ranges.append((state, cursor, cursor + count - 1))
        cursor += count
    assert cursor - 1 == TASKS_PER_PROJECT, "state plan must cover exactly 1,000 ids"
    return ranges


def _weighted_priority(rng: random.Random) -> str:
    draw = rng.random()
    running = 0.0
    for value, weight in PRIORITY_WEIGHTS:
        running += weight
        if draw <= running:
            return value
    return PRIORITY_WEIGHTS[-1][0]


def inner_main() -> int:
    """Seed the connected stack and print the manifest JSON on stdout."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.core.settings.prod")
    import django

    django.setup()

    from datetime import timedelta

    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.db.models import Count
    from django.utils import timezone

    from apps.accounts.services.tokens import issue_agent_token
    from apps.agents.services import open_session
    from apps.projects.services.projects import create_project
    from apps.tasks.models import Task, TaskDependency

    seed = int(os.environ.get("PERF_SEED", str(FIXTURE_SEED)))
    owner_username = os.environ.get("PERF_OWNER_USERNAME", DEFAULT_OWNER_USERNAME)
    owner_password = os.environ.get("PERF_OWNER_PASSWORD", DEFAULT_OWNER_PASSWORD)
    rng = random.Random(seed)

    if Task.objects.filter(created_by=SEED_MARKER).exists():
        print(
            "refusing to double-seed: perf-seed tasks already exist on this stack "
            "(use a fresh stack: python e2e/perf/stack.py down -v && up)",
            file=sys.stderr,
        )
        return 2

    User = get_user_model()
    owner, _ = User.objects.get_or_create(
        username=owner_username,
        defaults={"is_staff": False, "is_superuser": False},
    )
    owner.set_password(owner_password)
    owner.save(update_fields=["password"])

    projects = []
    for index in range(PROJECT_COUNT):
        project = create_project(
            name=f"perf-project-{index:02d}",
            repo_path=f"e2e/perf fixture project {index:02d} (no repo access)",
            default_branch="main",
            system_prompt_rules="WP-6.3 performance fixture (MT-6.3-01 seed).",
            actor_ref=SEED_MARKER,
        )
        project.agent_policy.max_concurrent_tasks = 10  # G-26 default is 1
        project.agent_policy.save(update_fields=["max_concurrent_tasks"])
        projects.append(project)

    ranges = _state_ranges()
    now = timezone.now()
    dependency_rows: list[TaskDependency] = []
    tasks: list[Task] = []
    for project in projects:
        project_tasks: dict[int, Task] = {}
        for state, first_n, last_n in ranges:
            for n in range(first_n, last_n + 1):
                task = Task(
                    id=f"{project.id}-T{n:03d}",
                    project=project,
                    title=f"Fixture task {n:04d}",
                    description="Deterministic WP-6.3 seed fixture (MT-6.3-01).",
                    acceptance_criteria=["Fixture criteria (seeded, never executed)."],
                    target_scope=["src/**"],
                    priority=_weighted_priority(rng),
                    state="in_progress" if state == "in_progress" else (
                        "pending" if state == "pending_blocked" or state == "pending_free" else state
                    ),
                    audit_required=True,
                    created_by=SEED_MARKER,
                )
                if state == "in_progress":
                    task.worker_agent_id = f"seed-holder-{project.id}"
                    task.worker_session_id = f"seed-hold-{project.id}-T{n:03d}"
                    task.claimed_role = "coder"
                    task.lease_acquired_at = now
                    task.lease_expires_at = now + timedelta(minutes=60)
                    task.lease_generation = 1
                if state == "in_human_review":
                    task.review_reason = "self_flagged"
                project_tasks[n] = task
                tasks.append(task)
        # Blocked chain: T295..T443 depend on the next blocked id, T444 on
        # the draft tail (T255) — every dependency is pending/draft, so the
        # work list's deps-completed filter never offers these 150 rows.
        for n in range(295, 444):
            dependency_rows.append(
                TaskDependency(task=project_tasks[n], depends_on=project_tasks[n + 1])
            )
        dependency_rows.append(TaskDependency(task=project_tasks[444], depends_on=project_tasks[255]))

    with transaction.atomic():
        for start in range(0, len(tasks), 500):
            Task.objects.bulk_create(tasks[start : start + 500])
        TaskDependency.objects.bulk_create(dependency_rows)
        for project in projects:
            # Keep the allocator's counter consistent with the seeded ids so
            # any API-created task continues at T1001 (never reuses an id).
            project.task_counter = TASKS_PER_PROJECT
            project.save(update_fields=["task_counter"])

    agents: list[dict[str, Any]] = []
    for index in range(AGENT_COUNT):
        project = projects[index % PROJECT_COUNT]
        _row, plaintext = issue_agent_token(owner, project.id, scopes=["coder"])
        label = f"perf-agent-{index:02d}"
        open_session(
            session_id=label,
            project_id=project.id,
            token_id=_row.pk,
            agent_label=label,
            client_name="wp63-perf-sim",
            capability="text_only",
            transport="http",
        )
        agents.append(
            {
                "index": index,
                "project_id": project.id,
                "session_id": label,
                "worker_agent_id": label,
                "token": plaintext,
            }
        )

    by_state = {
        row["state"]: row["total"]
        for row in (
            Task.objects.filter(created_by=SEED_MARKER)
            .values("state")
            .annotate(total=Count("id"))
        )
    }
    manifest = {
        "seed": seed,
        "owner": {"username": owner_username},
        "counts": {
            "projects": PROJECT_COUNT,
            "tasks": TASKS_PER_PROJECT * PROJECT_COUNT,
            "sessions": AGENT_COUNT,
            "tokens": AGENT_COUNT,
            "dependencies": len(dependency_rows),
            "tasks_by_state": by_state,
        },
        "projects": [project.id for project in projects],
        "agents": agents,
    }
    print(json.dumps(manifest))
    return 0


def host_main(argv: list[str]) -> int:
    """Copy this file into the backend container, run it, save the manifest."""
    from perf_common import MANIFEST_PATH, RUN_DIR, PerfError, compose_argv

    parser = argparse.ArgumentParser(
        description="Seed the WP-6.3 perf stack with the NFR-09 fixture (MT-6.3-01)."
    )
    parser.add_argument("--seed", type=int, default=FIXTURE_SEED)
    parser.add_argument("--project", default=None, help="compose project name")
    args = parser.parse_args(argv)

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()

    copy_cmd = compose_argv("cp", str(script), "backend:/app/perf_seed.py", project=args.project)
    copied = subprocess.run(copy_cmd, capture_output=True)
    if copied.returncode != 0:
        raise PerfError(
            "docker compose cp failed — is the perf stack up? "
            f"({copied.stderr.decode(errors='replace').strip()})"
        )

    owner_password = os.environ.get("PERF_OWNER_PASSWORD", DEFAULT_OWNER_PASSWORD)
    run_cmd = compose_argv(
        "exec",
        "-T",
        "-e",
        "PERF_SEED_INNER=1",
        "-e",
        f"PERF_SEED={args.seed}",
        "-e",
        f"PERF_OWNER_USERNAME={os.environ.get('PERF_OWNER_USERNAME', DEFAULT_OWNER_USERNAME)}",
        "-e",
        f"PERF_OWNER_PASSWORD={owner_password}",
        "backend",
        "python",
        "/app/perf_seed.py",
        project=args.project,
    )
    completed = subprocess.run(run_cmd, capture_output=True)
    stdout = completed.stdout.decode(encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        sys.stderr.write(stdout)
        sys.stderr.write(completed.stderr.decode(errors="replace"))
        raise PerfError(f"seed failed with exit code {completed.returncode}")

    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise PerfError("seed produced no manifest on stdout")
    manifest = json.loads(lines[-1])  # last line is the manifest JSON
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    counts = manifest["counts"]
    print(f"seed={manifest['seed']} projects={counts['projects']} "
          f"tasks={counts['tasks']} sessions={counts['sessions']} "
          f"tokens={counts['tokens']} dependencies={counts['dependencies']}")
    print(f"tasks_by_state={json.dumps(counts['tasks_by_state'], sort_keys=True)}")
    print(f"manifest written: {MANIFEST_PATH} (gitignored — contains agent tokens)")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if os.environ.get("PERF_SEED_INNER") == "1":
        return inner_main()
    return host_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
