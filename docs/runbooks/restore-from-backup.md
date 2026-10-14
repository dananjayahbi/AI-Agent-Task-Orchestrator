# Runbook: Restore from backup

> Source: parent plan Section 17 "Runbooks" row; procedure derived by actually
> performing the drill (WP-6.2, MT-6.2-04), not written in advance.
> This document is the source for the published Section 17 runbook page
> (MT-6.5-03) and the restore step of the VPS rehearsal (MT-6.6-02) —
> Section 20.5 traceability.

**Purpose:** restore system data (Postgres database + media volume) from the
second-location artifacts the daily backup trigger produces (NFR-04/NFR-05),
and verify the restored stack before switching traffic to it.

**Scope:** full-host restore. The artifacts live *outside* every Docker
volume (`infra/backup/README.md`), so this procedure works on a fresh host
whose volumes were never created.

---

## 0. Preconditions

* Docker Engine + Compose plugin on the host (same versions as documented in
  the parent plan Section 16.1).
* Access to the second location (default `infra/compose/backup-data/` on the
  host that ran the backups; `ORCHESTRATOR_BACKUP_HOST_DIR` if configured).
* The environment template `.env` for the stack (Section 16.2: real values
  live outside Git — **never** inline secrets in commands or this document).
* The backend image built (`docker compose build backend`) — it contains
  `pg_restore` (postgresql-client-16, `backend/Dockerfile`).

## 1. Pick the artifacts

```sh
ls -la <second-location>/database/     # pick orchestrator-<UTC>.dump — use the newest
ls -la <second-location>/media/        # the media mirror to copy back
```

Record the dump file name and its timestamp: it is the **recovery point
evidence** for this restore (the drill record lists it), and the stack's data
will be as of that moment, not as of now.

## 2. Bring up a fresh stack with empty volumes

A **fresh project name** guarantees new, empty volumes — this is what proves
the restore comes from the artifacts alone (MT-6.2-04 risk note: leftover
volumes make a drill pass for the wrong reason). Do not reuse the original
project name; do not start the original stack first.

```sh
export DRILL_PROJECT=orchestrator-restore-$(date -u +%Y%m%dT%H%M%SZ)
docker compose -p "$DRILL_PROJECT" \
  -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml \
  up -d postgres redis
```

Wait until healthy:

```sh
docker compose -p "$DRILL_PROJECT" -f infra/compose/compose.yaml \
  -f infra/compose/compose.dev.yaml ps
```

> On a **VPS/real host** the equivalent is simply "the host has no volumes
> yet": the default project name creates them empty on first `up`.

## 3. Restore the database from the dump

The dump is PostgreSQL custom format → restore with `pg_restore` (never
`psql` for this format). Credentials come from the environment template only.

```sh
docker compose -p "$DRILL_PROJECT" \
  -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml \
  run --rm --no-deps -T \
  -v "$(pwd)/<second-location-relative>/database:/restore:ro" \
  --entrypoint pg_restore postgres \
  --host postgres --username "${ORCHESTRATOR_DATABASE_USER:?}" \
  --dbname "${ORCHESTRATOR_DATABASE_NAME:?}" \
  --no-owner --no-privileges --exit-on-error \
  /restore/orchestrator-<UTC>.dump
```

`--exit-on-error` is mandatory: a partially-restored database must fail the
step, not limp into the smoke tests (Section 20.4 item 1).

## 4. Restore the media volume from the mirror

Copy the mirror into the fresh project's media volume (content-addressed keys
copy 1:1; the destination volume is empty, so a plain recursive copy is
complete):

```sh
docker compose -p "$DRILL_PROJECT" \
  -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml \
  run --rm --no-deps -T \
  -v "$(pwd)/<second-location-relative>/media:/restore:ro" \
  --entrypoint sh postgres \
  -c 'mkdir -p /media && cp -a /restore/. /media/ && find /media -name ".put-*" -delete'
```

(The final `find` removes any in-progress temp file the sync skipped anyway —
defence in depth; `.put-*` files are never valid objects, Section 16.3.)

> **Why postgres as the carrier:** it is the one service already in the
> project with both the network alias and a shell; the run is `--rm
> --no-deps` so it starts no second database. Any image with `sh` and the
> volume mounted works equivalently.

## 5. Bring up the full stack

```sh
docker compose -p "$DRILL_PROJECT" \
  -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml \
  up -d
```

`migrate` runs first (the restored schema is already current — a successful
`migrate` with nothing to apply is itself a check), then `backend`, `worker`,
`beat`, `web`. Wait for `backend` health:

```sh
docker compose -p "$DRILL_PROJECT" -f infra/compose/compose.yaml \
  -f infra/compose/compose.dev.yaml ps backend   # must reach "healthy"
```

## 6. Smoke checks (the WP-6.2 acceptance bar)

Run the drill runner, which executes the smoke checks and writes a JSON
results document:

```sh
python e2e/restore_drill.py --check-only --base-url http://127.0.0.1:<port>/api/v1
```

The checks (scope recorded in the drill record):

1. `GET /health/live` → 200 (process up)
2. `GET /health/ready` → 200 (database + cache reachable **with the restored
   data**)
3. `GET /api/v1/schema` → 200 (API serving)
4. Data-presence check: at least one restored row readable from the restored
   database (the drill seeds its own marker before taking the backup, so the
   restored stack answering proves the artifact path, not a fresh empty
   database)

A failure here means **the restore is not verified** — do not promote the
stack; see §8.

> The parent plan's full Section 18 scenario suite (happy path, crashed
> agent, escalation, merge conflict, screenshot, cross-project access) is the
> end-state bar for NFR-05; its ownership sits with the Section 18 suite
> owners. Whatever the suite's state at drill time, the drill record states
> exactly which checks ran — an incomplete suite is a finding to escalate,
> never a reason to lower the bar (MT-6.2-04 risk note).

## 7. Teardown (drill hosts only)

The drill uses a disposable project; removing it removes its volumes:

```sh
docker compose -p "$DRILL_PROJECT" -f infra/compose/compose.yaml \
  -f infra/compose/compose.dev.yaml down -v
```

On a real host, step 7 does not exist: the restored stack *is* the stack —
point `.env`, published ports and the tunnel at it and keep it running.

## 8. Failure handling

* **Dump won't restore (`pg_restore --exit-on-error` fails):** stop; the
  artifact is corrupt or was taken from an incompatible server version. Fall
  back to the next-newest dump and record the corrupt one as a finding.
* **Smoke fails but restore succeeded:** the stack is up with data but not
  verified — do not promote. Capture container logs
  (`docker compose -p "$DRILL_PROJECT" ... logs --tail=200`) into the drill
  record.
* **No artifacts / artifacts older than the retention window:** that is an
  operational failure of the daily trigger, not of this procedure — check the
  `beat` schedule and worker logs (`infra/backup/README.md`), then re-run the
  trigger manually before retrying.

## 9. Cadence and records

* **Weekly** (Section 16.5: "weekly restore drill documented and rehearsed"),
  including after **any** retention change (MT-6.2-03 risk note).
* Write a drill record per run: `docs/plan/wp-6.2-restore-drill-<date>.md`
  (format: WP-6.2 "drill record" deliverable — date, artifacts, environment,
  steps, smoke result, duration, findings, backup age).
* The automated runner for the whole procedure:
  `python e2e/restore_drill.py --help`.
