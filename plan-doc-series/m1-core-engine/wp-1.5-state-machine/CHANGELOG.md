# WP-1.5 State machine service and transition history: changelog

Short note per completed micro-task (Section 20.4, item 7).

## Unreleased

- **MT-1.5-01** — Transition registry and guard framework (Sections 8.1–8.3,
  9.1, 9.6; FR-TSK-03/04; ADR-010). New package
  `backend/apps/tasks/state_machine/` with one concern per file
  (Section 20.3): `registry` (the Section 8.2 table as data —
  `TransitionSpec` validates every From/To against the six canonical
  states and every actor against the Section 7.2 `owner|agent|system`
  triad at registration, so a non-canonical state is *unrepresentable*,
  not merely rejected later; `TransitionRegistry.resolve` answers the
  catalog `TASK_STATE_CONFLICT`/409 for any unmapped (from, trigger)
  pair), `hooks` (the **single** in-transaction event seam plus the
  narrow Section 9.8 review-push seam — both registerable, both no-ops
  until WP-1.9/WP-5.4 plug in; no second event mechanism invented),
  `guards` (shared predicates: active-lease reading, coder-lease
  clearing, dependency readiness), `loader` (idempotent one-shot
  registration), `transitions_owner`/`transitions_system`/
  `transitions_agent` (the rows themselves), and `dispatcher` —
  the generic execution path implementing Section 8.2's three universal
  rules in one `transaction.atomic()`: resolve → actor check →
  stub refusal → reason-catalog check → guards → side effects →
  Section 8.3 invariant assertions → exactly one `version` bump →
  exactly one Transition row → exactly one Event-hook call → push on
  `in_human_review` entry. Optimistic `expected_version` returns
  `VERSION_CONFLICT`; a failure anywhere (including inside the event
  hook) rolls back state, bump, history and event together (tested by
  forcing the hook to explode). Actor mismatches answer
  `TransitionActorForbidden` (403 `ROLE_NOT_PERMITTED`); a dispatch
  without an `actor_ref` or with a non-canonical actor is a `ValueError`
  (programmer error, never a wire response). The registration
  extension point (`register(..., replace=True)`) is how WP-1.6/WP-2.6/
  WP-3.x rewire or add rows — the dispatcher never names a concrete
  row. `TransitionNotWired` (500 `SERVER_ERROR`, the only catalog code
  that honestly describes an unwired server path) is defined here for
  MT-1.5-04. **T1 (create) is exempt from the registry by design**
  (MT-1.5-01 risk note): T1's From column reads *(new)* — no row, no
  from-state — and its side effects are the Section 7.3 INSERT that
  WP-1.4's `create_task` already performs ("T1's model-level step");
  the `task.created` event point stays there for WP-1.9's hook. Smoke
  tests (`tests/test_state_machine_framework.py`, 14 cases) cover
  legal dispatch, illegal/unknown pairs, stale versions, actor
  refusals, shape validation, duplicate/replace registration, hook
  rollback, the unwired-hook path, and the Section 9.1 placeholder
  scan.
- **MT-1.5-02** — Owner transitions T2/T3/T19 (Section 8.2; FR-TSK-03/04).
  `transitions_owner.py` transcribes the rows: **T2** publish
  (`draft→pending`; guards: non-blank title → else `VALIDATION_ERROR`
  400 through the standard envelope mapping, attachments readiness
  *vacuous until WP-1.11* — the hook point exists, no override flag
  invented, dependencies → `DEPENDENCY_UNMET` 409 via a new
  `DependencyUnmet` APIException; side effect: visibility *is* the
  `pending` state), **T3** unpublish (`pending→draft`; refuses while
  lease/worker records exist — even an expired-but-unswept claim, since
  the sweeper T5 owns clearing, recorded reading), **T19** archive
  (all five non-`completed` states → `to_state=None` flag row; side
  effect is WP-1.4's `archive_task` setter adopted through the
  side-effect return contract so the dispatcher never double-bumps the
  version; `completed` refuses; re-archive never re-stamps the marker
  but still records the dispatch). Tests
  (`tests/test_owner_transitions.py`, 17 cases) assert every happy
  path, guard failure, actor refusal, and the FR-TSK-04 history row
  (actor, from/to, reason, note, timestamp).
- **MT-1.5-03** — System transitions T5/T9 (Section 8.2, 8.4, 8.6,
  9.6, 9.8; FR-LEA-04/07; G-10). `transitions_system.py`: **T5**
  (`in_progress→pending`; guard `lease_expires_at < now` — future and
  null leases refuse; `failure_retry_count+1`, worker fields cleared
  via the shared helper, event `task.lease_expired` asserted to be a
  Section 9.6 catalog entry) and **T9** (`in_progress→in_human_review`;
  guard `failure_retry_count >= max_retries` read from the project
  policy — default 3; `review_reason=retry_exhausted` canonical; the
  Section 9.8 push fires from the dispatcher's generic
  `in_human_review`-entry rule with dedupe key `(event type, task id,
  state version)` on the payload). **Recorded reading (parent open
  decision):** T9 also clears the worker/lease fields although its
  Side-effects cell does not list it — Section 8.3 invariant 1 ("no
  coder lease outside `in_progress`") would otherwise break on the
  sweeper's Flow-B escalation straight from `in_progress`. Boundary
  tests pin `max_retries - 1` (T5 still allowed, T9 refused) vs
  `max_retries` (escalation applies), system-only actors, and all five
  non-`in_progress` refusals (`tests/test_system_transitions.py`,
  22 cases).
- **MT-1.5-04** — Agent transition stubs T4/T6/T7/T8 (Section 8.2;
  FR-MCP-03). `transitions_agent.py` registers the four rows with their
  exact From/To/Actor shape, `wired=False` plus a `stubbed_by` marker
  (WP-1.6 for T4/T6, WP-2.6 for T7/T8), and guard/side-effect callables
  that raise `TransitionNotWired` (500 `SERVER_ERROR`) — the
  dispatcher refuses stubs even earlier, right after the actor check,
  so state, `version`, history and events stay untouched (tested for
  all four). Guard/side-effect **docstrings carry the table cells
  verbatim** (asserted fragment-by-fragment) as the wiring contract;
  the stable `(task, context)` signature reads caller-specific inputs
  from `context.extra` (session, resolution, human-attention evidence)
  so wiring never reshapes the callables (MT risk note). T8's reason
  pair is frozen as `T8_REVIEW_REASONS = (self_flagged,
  scope_violation)` (Section 8.4, tested). The override test rewires
  T4 through `register(replace=True)` to a full claim-shaped side
  effect and dispatches it successfully — the extension point works
  without touching the dispatcher
  (`tests/test_agent_transition_stubs.py`, 18 cases).
- **MT-1.5-05** — Append-only Task Transition history model
  (Section 7.2, 7.4 rule 5; FR-TSK-04; P8). `models/transitions.py`
  (file-per-entity layout): exactly the nine Section 7.2 fields —
  literal field-set test included, FK named `task` so the column is
  `task_id` (the WP-1.4 `project_id` naming decision again), `id` as
  the auto pk; `from_state`/`to_state` choices **and** DB
  CheckConstraints on the six canonical states, `actor_type` choices +
  DB check on the three canonical actors (ADR-010, frozen sets are
  DB-checked); `reason_code` publishes the closed `TransitionReason`
  choices = the Section 8.4 twelve + the Section 8.2 trigger codes
  (boundary-checked only — the set grows when WP-3.x registers rows,
  and a frozen column would block the catalog-first rule; recorded
  here as the split decision). Append-only is enforced at the
  application layer: custom queryset refuses `update`/`delete`/
  `bulk_update`, model `save()` refuses post-insert, model `delete()`
  refuses — all raising `TransitionHistoryImmutable`; the only write
  path is the dispatcher inside its transaction. Migration
  `0003_tasktransition.py` is model-only (Section 20.3) with a
  per-task chronological index `(task, timestamp)`. Tests
  (`tests/test_transition_history.py`, 8 cases) prove the field set,
  value catalogs, DB refusals, every immutability door, one complete
  row per dispatch, and clean migration apply/reverse
  (`migrate tasks zero` → re-apply).
- **MT-1.5-06** — Exhaustive transition matrix (Sections 8.1–8.3, 18;
  FR-TSK-03/04; NFR-01). `tests/test_transition_matrix.py` builds its
  parametrization **from the registry at collection time** (9
  registered triggers × 6 canonical states = 54 cases, exhaustiveness
  asserted): 13 legal pairs each dispatch to the registered target
  with exactly one history row, one event of the row's catalog type,
  the right push count (only `in_human_review` entries), the T19 flag
  semantics, and the stub not-wired failure path; 41 illegal pairs each
  answer `TASK_STATE_CONFLICT` 409 with state, `version`, history and
  events untouched. The Section 8.2 row *shape* is pinned by a literal
  transcription test (traceability), stub rows are marked for
  WP-1.15's wiring re-check, and the Section 8.3 invariants run at
  dispatch time: a probe row reaching `completed` without
  `merge_status=merged` refuses (rollback proven), the OQ-06
  `merge_strategy=manual` exception passes, a probe leaving
  `in_progress` with a coder lease refuses, a probe entering
  `in_progress` workerless refuses. The Section 9.1 direct-write rule
  is a production-tree scan (`tests/wp15_helpers.find_state_writes`)
  whose result set must be *exactly* the dispatcher's single
  `to_state` assignment — self-tested against dirty/clean samples so
  the scan cannot pass vacuously. Coverage of the state machine is
  measured with ephemeral `uv run --with coverage` (see WP notes —
  `pytest-cov` is not in the dev dependencies).

## WP notes, deviations and open questions

* **T1 create exemption (decided, MT-1.5-01 risk note).** Creation
  stays outside the registry: T1's From is *(new)*, which cannot be
  expressed in the six canonical states, and WP-1.4 already implements
  T1's side effects as the creating-transaction INSERT. Not raised as
  an OQ — the plan's own row wording settles it; the `task.created`
  emission point remains in `create_task` for WP-1.9's hook.
* **T2 "dependencies exist" reading (implemented + OQ candidate).**
  Implemented as *exists **and** completed* per MT-1.5-02's own risk
  note, sharing `all_dependencies_completed` with T4 and surfacing
  `DEPENDENCY_UNMET` (which the MT's acceptance criteria name, making
  the guard reachable). MT-4.5-06 phrases the web gate as
  "non-existent dependencies block publish" — existence-only would
  make the guard vacuous (FK edges always exist) and the acceptance
  criterion untestable. **OQ candidate (next free `OQ-15+` id in
  Section 22):** confirm T2 requires *completed* dependencies at
  publish time, or relax to existence-only and drop the
  `DEPENDENCY_UNMET` acceptance bullet.
* **T9 worker clearing vs Section 8.3 invariant 1 (decided).** T9
  clears the worker/lease fields (see MT-1.5-03 note). The table's
  Side-effects cell is read together with the invariants the same plan
  makes mandatory; the alternative (stranding a coder lease on
  `in_human_review`) is explicitly forbidden by invariant 1.
* **Event-row sequencing (hook seam implemented + OQ candidate).**
  The dispatcher calls one in-transaction hook; until MT-1.9-02
  registers the Event-row writer it is a no-op — no second event
  mechanism was invented (MT-1.5-01 risk note). Rollback and
  exactly-once behavior are already tested at the seam.
  **OQ candidate (next free `OQ-15+` id):** is the no-op-until-WP-1.9
  sequencing acceptable (events absent from history until 1.9 lands),
  or should a minimal Event row land inside WP-1.5? The plan sequences
  1.9 after 1.5 (Section 20.6) and MT-1.9-02 explicitly wires the
  helper into this service, which is why the seam — not a row — ships
  here.
* **Transition endpoint deferral (decided per MTs).**
  `POST /tasks/{id}/transition` is *not* landed: MT-1.5-02 lists the
  HTTP wiring as out of scope (service behavior asserted in-process;
  endpoint verification is WP-1.15's). The drift guard
  `DEFERRED_ENDPOINTS` entry in `tests/test_authorization_matrix.py`
  keeps its 404 assertion with a comment recording the decision; the
  "Publish tasks" matrix row continues to run on its probe.
* **Wire codes (Section 20.4 item 5).** New exceptions stay inside the
  closed 19-code catalog: `DependencyUnmet` → `DEPENDENCY_UNMET` 409
  (resource-condition refusal, not a malformed payload),
  `TransitionActorForbidden` → `ROLE_NOT_PERMITTED` 403 (the same
  code the authorization matrix produces for role refusals),
  `TransitionNotWired` → `SERVER_ERROR` 500 (the catalog has no
  `NOT_IMPLEMENTED` and a 20th code is forbidden — an unwired server
  path *is* a server error). Illegal/stale pairs keep
  `TASK_STATE_CONFLICT`/`VERSION_CONFLICT` at 409.
* **Trigger codes (derived, not invented).** Trigger/reason machine
  values are the snake_case Trigger column of Section 8.2
  (`publish`, `unpublish`, `archive`, `lease_expired`,
  `retry_exhausted` — already a Section 8.4 member, `claim`,
  `voluntary_release`, `submit`, `submit_flagged`); T8's cell
  ("Submit (self-flagged) or scope violation") abbreviates to
  `submit_flagged` because a snake_case of the whole cell would be
  unusable as a wire value — flagged here as the single derivation.
  Later rows extend `TransitionReason` first (catalog-first).
* **Append-only gap closes with WP-1.9.** Application-level refusal is
  complete; until MT-1.9-04 applies REVOKE UPDATE/DELETE, a raw-SQL
  writer could still mutate history (MT-1.5-05 risk note). No update/
  delete API exists to bypass either.
* **Actor triad vs Section 8.2 letters.** `actor_type` stores the
  Section 7.2 triad; O→`owner`, C/A/M→`agent`, S→`system`. The
  coder-vs-auditor distinction inside `agent` belongs to the wiring
  WP's authorization (it knows the caller's role) — the registry keeps
  history columns canonical.
* **Event/push triggers emitted.** T2/T3/T19/T9 → `task.transitioned`,
  T4 → `task.claimed`, T5 → `task.lease_expired`, T6 →
  `task.released` — all Section 9.6 catalog members (asserted). Push
  fires generically for every `in_human_review` entry (Section 9.8's
  trigger list — retry exhaustion is one of them), so WP-3.x's T14/T18
  inherit it without touching T9 (the MT's seam-keeping risk note).
* **Scope guard for direct writes.** `find_state_writes` scans
  `backend/apps` production code only; test fixtures may set `state`
  freely (they build pre-conditions), and `Task.objects.create(state=…)`
  is T1's documented create exemption — the scan's pattern set is
  narrow by design (MT-1.5-06 risk note) and self-tested.
