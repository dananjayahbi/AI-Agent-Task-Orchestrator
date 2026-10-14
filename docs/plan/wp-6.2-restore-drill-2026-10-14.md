# WP-6.2 restore drill record — 2026-10-14

Drill record deliverable (MT-6.2-04; parent plan Section 19 WP-6.2, Section
20.4 item 1). Format per `docs/runbooks/restore-from-backup.md` §9: date,
artifacts, environment, steps, smoke result, duration, findings, backup age.

## Outcome

| Field | Value |
| --- | --- |
| **Outcome** | **PASS** (second run; first run failed — see Findings) |
| Date (UTC) | 2026-10-14, 03:15:10 – 03:18:37 |
| Duration | 206.2 s (15 phases, all pass) |
| Runner | `python e2e/restore_drill.py` (repo root, exit code 0) |
| Evidence | `e2e/restore_drill_results.json` — `"outcome": "pass"`, `"findings": []` |
| Host | Windows, Python 3.14.0, Docker 29.7.2, Docker Compose v5.4.0 |
| Restore project | `wp62-drill-restore-20261014-031510` (new timestamped project; fresh volumes **by construction**) |

## Scope

Full Section 16.5 round-trip on a local host: disposable source stack with
fresh volumes → seed marker row + content-addressed media object → run the
real daily backup task (`backup.run_daily_backup`) on the live worker →
teardown source **including volumes** → restore from the second-location
artifacts only into a brand-new project → smoke the restored stack →
teardown. Isolated project names (`wp62-drill-src`, `wp62-drill-restore-*`)
and loopback ports (8017/3017) keep it clear of every other stack.

**Smoke scope (stated explicitly, per MT-6.2-04 risk note):** the parent
plan's Section 18 scenario suite (happy path, crashed agent, escalation,
merge conflict, screenshot, cross-project access) did not exist at drill
time. What ran is the runbook §6 smoke-level suite: `/health/live`,
`/health/ready`, `/api/v1/schema`, marker-row positive control, media-object
positive control, worker ping — plus the drill's freshness proofs. The
Section 18 suite remains a finding to escalate to its owners, not a lowered
bar.

## Artifacts used (second location only)

| Artifact | Value |
| --- | --- |
| Backup dir | `infra/compose/backup-data/` (host bind mount, git-ignored) |
| Database dump | `orchestrator-20261014T031634Z.dump`, 92 112 bytes, sha256 `fb8dec8a7c4dc65adaf0a9ba6a16ae455aaeee09dd5c643147c8fd45376e6992` |
| Media marker key | `objects/16/163cf7f579f2732dd3e32d67a359d1d50a6d6ea19149ec87b983417dbc0882d4` (mirrored: yes) |
| Marker row | `drill-marker-20261014-031510` (unusable-password user) |
| Backup age at restore | **~25 s** — dump taken 03:16:35Z, `pg_restore` ran 03:17:00Z. Artifact freshly produced by the drill's own trigger run (see Follow-ups for the age caveat). |

## Steps executed and per-phase results

All phases from `e2e/restore_drill_results.json` (status / duration):

1. `preflight` — pass / 11.8 s (compose config validated, backend image built)
2. `source_stack_up` — pass / 48.9 s (project `wp62-drill-src`, `--wait`)
3. `seed_markers` — pass / 16.0 s (marker user + content-addressed media object)
4. `backup_trigger_run` — pass / 6.7 s (`celery call backup.run_daily_backup`
   on the live worker — the exact task the daily beat entry dispatches)
5. `beat_schedule_check` — pass / 5.9 s (in-container proof of the beat entry:
   `<crontab: 0 2 * * * (m/h/dM/MY/d)>` — UTC, defaults 02:00)
6. `collect_artifacts` — pass / 0.0 s (dump sha256 + media marker recorded above)
7. `source_teardown_with_volumes` — pass / 10.1 s (`down -v` — only the
   second location survives)
8. `restore_stack_up_fresh` — pass / 7.7 s (new timestamped project ⇒ empty
   volumes; `postgres` + `redis` only)
9. `freshness_proof` — pass / 2.7 s (**negative controls**: 0 public tables,
   media marker absent before any restore byte)
10. `restore_database` — pass / 3.2 s (`pg_restore --exit-on-error
    --no-owner --no-privileges`, password via container env only)
11. `restore_media` — pass / 2.2 s (mirror copied back over `/media/`)
12. `restore_stack_full_up` — pass / 48.7 s (full Section 16.1 topology;
    `migrate` a no-op against the restored schema)
13. `smoke_http` — pass / 2.1 s (`/health/live` 200, `/health/ready` 200,
    `/api/v1/schema` 200)
14. `smoke_data_controls` — pass / 30.4 s:
    * marker row restored — `count == 1` ✓
    * media object restored — content equals the marker id ✓
    * worker ping — `pong`, 1 node online ✓
15. `restore_teardown` — pass / 9.7 s (`down -v`, drill stacks removed)

## Findings (first run, 00:41–00:43 UTC, `"outcome": "fail"`)

The first execution of the drill failed at `smoke_data_controls` with
`marker user count after restore = '21 objects imported automatically (use
-v 2 for details).\n\n1'`.

**Diagnosis — drill-check flaw, not a restore bug.** The captured stdout
ends in `1`: the marker row *was* restored (the restore phases and both
freshness negative controls had passed). The extra banner is printed by
**Django 5.2's own `shell` management command**
(`django/core/management/commands/shell.py`) to stdout before it executes
`-c` code — it auto-imports the 21 installed models and reports that at
verbosity 1. The check compared the *whole* stdout against `"1"`, so a
successful restore was misreported as a failure. `backend/apps/backup/` was
not implicated: the dump restored cleanly and the row was present.

**Fix applied (no acceptance checkbox was ever marked on this basis):**

* `e2e/restore_drill.py` — the marker query now runs with
  `manage.py shell --no-imports` (banner suppressed at the source) and the
  captured output is parsed via the new `_last_output_line()` helper (belt
  and braces: even a noisy capture yields the printed count). The check
  detail now also records the raw stdout.
* `backend/tests/test_restore_drill_marker_check.py` (new) — regression
  test pinning the parse against the exact failed-run capture and asserting
  the drill passes `--no-imports`.

**Second run:** full drill re-executed end-to-end on the same day —
`"outcome": "pass"`, all 15 phases and all 6 smoke checks pass,
`"findings": []` (`e2e/restore_drill_results.json`).

## Follow-ups

* **Section 18 scenario suite** (pre-existing finding, restated): the six
  scenarios beyond smoke level have not been run against a restored stack;
  ownership sits with the Section 18 suite owners (escalate, don't lower the
  bar).
* **Backup age:** this drill's artifacts were minutes old by design (the
  drill creates its own source stack and triggers its own backup — it proves
  the *path*, not long-term durability). Per Section 16.5's weekly cadence,
  later runs should also rehearse restoring **older** artifacts, and real
  off-host durability still depends on operators pointing
  `ORCHESTRATOR_BACKUP_HOST_DIR` at a second disk/network mount (decision:
  `docs/plan/wp-6.2-backup-retention-decision.md`).
* Retention cadence and record location are documented in
  `docs/runbooks/restore-from-backup.md` §9 and `infra/backup/README.md`.

## Environment

| Component | Version / value |
| --- | --- |
| Host OS | Windows |
| Python (runner) | 3.14.0 (stdlib-only script) |
| Docker Engine | 29.7.2 |
| Docker Compose | v5.4.0 |
| Postgres server (compose) | postgres:16 (client pinned `postgresql-client-16`) |
| Backend image | built by the drill's preflight (`apps.backup` + `pg_dump` present) |
| Beat schedule | `0 2 * * *` UTC (`ORCHESTRATOR_BACKUP_TRIGGER_HOUR` default) |
| Ports | backend 127.0.0.1:8017, web 127.0.0.1:3017 (drill defaults) |

## Re-run

```sh
python e2e/restore_drill.py            # full drill; writes e2e/restore_drill_results.json
uv run pytest tests/test_restore_drill_marker_check.py tests/test_backup.py -q   # from backend/
```
