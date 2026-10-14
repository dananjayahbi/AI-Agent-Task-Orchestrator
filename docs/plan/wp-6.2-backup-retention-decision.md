# Backup retention decision (WP-6.2, MT-6.2-03) — sibling of OQ-10

> **Status: recorded, flagged for plan-owner confirmation.** The parent plan
> `ai_agent_task_orchestrator_architecture_plan.md` is the single source of
> truth; this note documents the conservative default MT-6.2-03 prescribed and
> must be confirmed against Section 22 when the plan owner closes OQ-10
> (MT-6.2-03 risk note: "record it as a decision next to OQ-10 and mark it for
> plan-owner confirmation; do not silently invent a number or silently drop the
> policy").

## Why this decision exists

Section 22's **OQ-10** covers *data* retention — events (recommended 1 year),
checkpoints/patches (180 days after completion), attachments (archive + 30
days) — and is **deferred to M6 with a recommended default**. It names no
backup retention. Section 16.5 requires a daily dump and media sync to a
second location and a weekly restore drill, and Section 9.9's retention
cleanup job is a separate row about checkpoints/patches/orphaned *data*, not
about backup artifacts. So backup retention is an open sibling decision:
without it the second location grows without bound (MT-6.2-02 risk note), and
with a thoughtless pruning rule a bug there destroys the only copies
(MT-6.2-03 risk note).

## The decision

**Database dumps** (`<second location>/database/orchestrator-<UTC>.dump`):

| Parameter | Setting | Default | Meaning |
|---|---|---|---|
| Age window | `ORCHESTRATOR_BACKUP_RETENTION_DAYS` | **14 days** | Dumps older than this are pruned by the daily trigger's retention step. |
| Keep floor | `ORCHESTRATOR_BACKUP_MIN_KEEP` | **7 dumps** | The newest N are **never** pruned, regardless of the age window. |

* **Why 14 days:** a conservative default that survives *noticing corruption
  late* — restore drills and corruption discovery both happen days after the
  fact, not minutes (MT-6.2-03 risk note's suggested reasoning: "keep enough
  daily points to survive noticing corruption late"). Two weeks of daily
  points costs kilobytes-to-megabytes per day for a small stack, so the cost
  of the doubt is negligible against the cost of the doubt being wrong.
* **Why a floor of 7:** pruning runs against the *second location*, where a
  bug destroys the only copies. The floor guarantees a week of restorable
  artifacts even if the age configuration is mis-set to something destructive
  (MT-6.2-03: "never prune the newest N backups regardless of age
  configuration").
* **What never gets pruned by this policy:** files that don't match the
  timestamped dump name (operator-made copies are recognized and spared) and
  **the media mirror** (below).

**Media mirror** (`<second location>/media/...`): **not pruned by the backup
retention step.** Reasons, in order:

1. Deletion of *data* is the Section 9.9 retention-cleanup job's decision
   under OQ-10; the backup must not pre-delete what that policy may still
   need (MT-6.2-02 explicitly assigns deletion to "the retention job's job").
2. The mirror is content-addressed and incremental (Section 16.3): it only
   grows when live data changes, so its growth rate equals the live volume's —
   bounding it is exactly the OQ-10 attachment-retention question, not an
   independent one.
3. An over-eager prune here "can quietly turn a backup into a mirror of a
   corrupted volume" (MT-6.2-02 risk note).

When OQ-10 closes on attachment retention, revisit this note: a principled
mirror policy would delete mirror objects that OQ-10 says the *live* volume
would no longer hold, **only after** the drill has proven the pairing. Until
then, the mirror accumulates and the host-side operator can archive or drop
whole mirror generations manually if disk pressure demands it.

## How pruning runs

The third step of the same daily backup trigger (`apps/backup/retention.py`,
task `backup.run_daily_backup`) — deliberately **kept separate from the
Section 9.9 retention-cleanup job** (MT-6.2-03 scope), and deliberately run
*after* a successful dump and sync: a failed backup day can never shrink the
set of restorable artifacts. The step fails loudly (not silently) on an
unusable configuration (`< 1` for either parameter), per Section 9.10
fail-fast: a typo must not silently delete every backup.

**Any change to this policy or the retention code requires re-running the
restore drill** (MT-6.2-03 risk note) and updating this note.

## Relationship to OQ-10 (Section 22)

| | OQ-10 (data retention) | This note (backup retention) |
|---|---|---|
| Covers | Live rows/objects: events, checkpoints, patches, attachments | Backup artifacts: dumps, media mirror |
| Recommended default in plan | events 1y; checkpoints/patches 180d; attachments archive+30d | none — open |
| Status | Deferred to M6, plan owner decides | Conservative default recorded here by MT-6.2-03, flagged for plan-owner confirmation |
| Coupling | Attachment decision may later justify mirror pruning (see above) | Dumps decision is independent of OQ-10's numbers |

## Confirmation

- [ ] Plan owner confirms or adjusts `14 days / keep 7` and the
      media-mirror stance when reviewing this next to OQ-10.
- [ ] If adjusted: update `apps/core/settings/base.py` defaults,
      `infra/compose/.env.example`, `configuration.md` rows, this note, and
      re-run the restore drill (record under `docs/plan/`).
