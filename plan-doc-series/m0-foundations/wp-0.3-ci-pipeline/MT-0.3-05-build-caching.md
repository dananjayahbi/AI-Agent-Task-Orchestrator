# MT-0.3-05 — Add Build Caching to Keep the Pipeline Under 10 Minutes

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.3-05 |
| Title | Add build caching to keep the pipeline under 10 minutes |
| Parent WP | WP-0.3 — CI pipeline (Milestone M0) |
| Requirements | NFR-07, NFR-11 |
| Priority | S |
| Dependencies | MT-0.3-01, MT-0.3-02, MT-0.3-03, MT-0.3-04 |
| Parent sections | 18, 19.1 (WP-0.3 acceptance), 20.4 |

## Context
WP-0.3's acceptance criterion is that the skeleton pipeline completes in under 10
minutes while every gate stays blocking. As the lint, test, build, and scan jobs
accumulate, uncached dependency installation dominates runtime. This task adds
appropriate caching — Python/`uv` caches, npm cache, and container layer reuse — so
the pipeline meets the budget without weakening any gate.

## Inputs / Prerequisites
* MT-0.3-01..04 — all pipeline jobs in place to measure and optimize.
* Parent plan 19.1 WP-0.3 — "pipeline under 10 minutes for the skeleton".
* Parent plan Section 18 — full gate list (caching must not skip a gate).
* Runner environment details (cache storage available on the CI platform).

## Scope (in)
* Add caching for Python dependency resolution (`uv`/pip caches) in backend and bridge
  jobs, keyed on the lockfile.
* Add npm (or chosen package manager) cache for the web job, keyed on the lockfile.
* Enable Docker layer caching for the container build job.
* Confirm cache keys invalidate correctly on dependency changes (no stale-cache false
  greens).
* Measure cold and warm pipeline duration and record both; warm pipeline must be under
  10 minutes.
* Add a WP changelog note.

## Out of scope
* Splitting or parallelizing jobs beyond current structure — only if required to meet
  the budget after caching; record any such change in the changelog.
* Skipping or soft-failing any gate to save time — gates remain blocking (WP-0.3
  acceptance).
* Test result caching or compiled-artifact publishing — not in the parent plan.
* Ongoing pipeline performance tuning in M6 — WP-6.3/WP-6.4.

## Target paths
* `.github/workflows/` — cache configuration in existing jobs
* CI workflow notes or `CONTRIBUTING.md` — measured durations
* WP changelog entry

## Acceptance criteria
- [ ] Python, npm and Docker build caches are configured and keyed on lockfiles/
  Dockerfiles.
- [ ] A dependency bump demonstrably invalidates the relevant cache (no false greens).
- [ ] Warm pipeline run completes in under 10 minutes, measured and recorded
  (WP-0.3 acceptance).
- [ ] No gate is skipped, weakened, or made non-blocking to save time.
- [ ] No secrets in cache configuration; caches contain no credential material
  (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the full pipeline twice in a row and compare durations (e.g. `gh run list --json
displayTitle,createdAt` plus per-job times, or the workflow's own timing summary);
the second (warm) run must report a total under 10 minutes with every required check
green.

## Attachments
* [Section 19.1 — WP-0.3 acceptance criteria](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Cache poisoning or stale caches can mask failures — key caches on lockfiles, scope
  them per branch trust rules, and never cache gate outputs.
* The 10-minute budget is for the skeleton; adding real test suites in M1 may exceed
  it — treat the budget as re-measured at each milestone, and raise a follow-up rather
  than disabling gates.
