# WP-6.5 — Documentation and runbooks — Changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

**MT-6.5-01 — Write the operator setup guide (done).**

Guide location (recorded per the MT risk note): **`docs/setup.md`** — the
top-level `docs/` choice the risk note explicitly offers; no new undocumented
docs area, no collision with `docs/plan/` (plan/report area). Linked from the
root `README.md` and `CONTRIBUTING.md` Documentation sections (MT target
paths), so it is one hop from the doc tree.

What landed, per the MT's Scope lines:

* Prerequisites; fresh-clone bring-up as **one documented command path**
  (WP-0.2's one-command health bring-up: env copy →
  `up -d --wait --wait-timeout 180` → `ps`); environment-template walkthrough
  of every Section 9.10 group as headed in `infra/compose/.env.example`, with
  the Section 16.2 required-in-prod/weak rules and the configuration.md
  naming rule; `dev`/`prod` profile table with tunnel opt-in;
  service-by-service health verification (Section 16.1 checks plus
  `/health/live` and `/health/ready` response bodies); tear-down with
  data-preservation notes; **upgrade and rollback chapter** (WP-6.5 named
  deliverable) built on Section 16.5 — pull → rebuild → one-shot migrate →
  `up --wait`, the `X-API-Version`/major-`1` bridge gate (Section 10.11,
  `bridge/src/orchestrator_bridge/transport.py`), rollback via previous
  pinned `ORCHESTRATOR_IMAGE_*` tags, reversibility caveat routed to the
  drill-derived restore runbook; VPS pointer summarizing Section 16.4's
  checklist with the parent plan as authority.
* Link targets landed (Section 20.5): MT-5.10-04's distribution path
  (`mobile/docs/distribution.md`, which in turn names this guide as its link
  target) + signing/build/checklist siblings; WP-6.2 backup/restore docs
  (`infra/backup/README.md`, `docs/runbooks/restore-from-backup.md`,
  `docs/plan/wp-6.2-restore-drill-*.md`, retention decision); sibling pointers
  to `docs/agent-guides/` (MT-6.5-02), `docs/runbooks/` (MT-6.5-03) and
  MT-6.5-04's plan doc.
* Feature set documented **as it exists**, never overclaimed: operator-blocked
  items are cited by their recorded Deferred entries — iOS/TestFlight and
  real-device checklist execution (MT-5.10-03/05, WP-5.10 changelog
  `### Deferred`), verified client-matrix rows (MT-2.11-02…07, WP-2.11
  changelog `### Deferred`), and the outstanding off-repo keystore backup
  (`mobile/docs/release-signing.md`). Push/FCM is documented as template
  shape only (`ORCHESTRATOR_PUSH_ENABLED` default `false`).

Evidence (the MT's test command, executed this batch — commands run verbatim
from `docs/setup.md` against an **isolated scratch Compose project with fresh
volumes** created from the committed template, `-p <scratch>` the only added
flag; scratch project, env file and backup dir removed afterwards, `git
status` clean of them):

* Bring-up: documented dev invocation → `EXIT=0`; `migrate` `exited (0)`,
  all other services `healthy`; first-run window matched the README.
* Health: `exec backend` probes returned exactly
  `{"status":"ready","checks":{"database":"ok","cache":"ok"}}` and
  `{"status":"live"}`.
* Upgrade chapter executed end-to-end: manual backup invocation → fresh
  `orchestrator-20261015T072610Z.dump` + media mirror in the second
  location; `pull postgres redis` `EXIT=0`; `build backend worker beat`
  `EXIT=0`; `run --rm migrate` `EXIT=0` (applied `notifications.0001/0002`,
  `tasks.0010/0011` on the scratch DB); `up -d --wait` again `EXIT=0`
  (migrate re-ran as the gate); `stop web` `EXIT=0`; `--profile prod
  config` renders exactly the Section 16.1 eight services.
* Tear-down: both documented forms `EXIT=0`.
* Doc checks: link checker over `docs/setup.md` → 32 relative links, 0
  missing; regex scan for secret-shaped strings and absolute host paths → 0
  matches; all 5 ```powershell blocks parse clean via the PowerShell
  parser.

Verified finding folded into the guide: plain `down` **without** the started
profile exits 0 but leaves profile-gated services running (verified: dev
`mailhog` survives) — the guide therefore documents `--profile dev down`.

Plan-update suggestions (gaps recorded, not fixed here — out of scope per
the MT): (1) `infra/compose/README.md` "Tear-down" omits the profile flag
(WP-0.2 doc, suggest a follow-up); (2) Section 16.1 lists `web` as a Next.js
image, but `infra/compose/compose.yaml` still builds the WP-4.1 placeholder
(`stubs/web/default.conf`, tag `orchestrator-web:stub`) while the real board
ships in `web/` and runs host-side per `web/README.md` — the guide documents
both facts; suggest plan/compose follow-up to wire the real image.

### Deferred

**MT-6.5-02 — Write the per-client agent guides (deferred).**
Blocker: **MT-2.11-07** (custom-agent template + verified matrix rows) —
operator-excluded: its own WP-2.11 changelog `### Deferred` records
MT-2.11-02…06 blocked on client credentials absent from this environment
(Claude, Copilot, OpenCode, Aider, DeepSeek keys), so the matrix may only be
filled from verified runs that cannot happen here. Its other inputs now
stand: MT-6.5-01 (done, entry above) and MT-2.12-04 (recorded
2026-10-13 in the WP-2.12 changelog). The operator guide links
`docs/agent-guides/` (index + matrix live) meanwhile.

**MT-6.5-03 — Write the runbooks from parent plan Section 17 (deferred).**
Blocker: **MT-2.11-07** (same operator-excluded record) for the "onboard a
new agent client" runbook's client pages; also pending MT-6.1-03 (verified
token lifecycle for the rotate-tokens runbook), owned by WP-6.1. Remaining
dependencies are recorded done: MT-0.1-06 stubs, MT-6.2-04 restore
procedure/drill (WP-6.2 changelog), MT-6.4-01/02 metrics and alert rules
(WP-6.4 changelog). The seven stubs in `docs/runbooks/` stay content-owned
by this MT; the operator guide links them as planned content.

**MT-6.5-04 — Write the troubleshooting guide (deferred).**
Blocker: chains on MT-6.5-02 and MT-6.5-03 (both deferred above — its
Dependencies row requires the agent guides and the runbooks to route into,
plus MT-6.4-01/02 which are done).
