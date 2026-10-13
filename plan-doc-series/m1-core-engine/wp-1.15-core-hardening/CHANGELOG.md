# WP-1.15 — Core engine test and hardening suite: changelog

## MT-1.15-06 — dashboard summary endpoint (gap closure)

- **`GET /dashboard/summary` lands (Section 9.2 Dashboard row, caller Owner;
  FR-MOB-01).** The row sat in the catalog with no owning micro-task until
  WP-5.6's "Dashboard endpoint gap" note recommended authoring one (MT-1.6-09
  precedent for unowned-endpoint follow-ups). The endpoint is read-only,
  Owner-session-only (`IsOwnerSession`), and aggregates per project, in
  project-id order: `state_counts` (always the six canonical G-01 keys,
  zero-filled; non-archived tasks only — T19 default visibility), `velocity`
  and `active_agents`. Payload shape matches the WP-5.6 recommendation and the
  hand-authored mobile `DashboardSummary` reconciliation contract exactly:
  `{projects: [{project_id, name, state_counts, velocity, active_agents}]}` —
  no pagination (single-resource GET, pagination.md), no invented fields (the
  needs-review banner derives from `in_human_review` on the client), no event
  emissions (Section 9.6 catalog has no dashboard event).
- **Documented defaults, not plan facts (Section 20.1 item 5):** `velocity` is
  pinned as the count of the project's completions in a trailing **7-day**
  rolling window from the append-only TaskTransition log (`to_state=completed`,
  server clock); `active_agents` counts AgentSession rows with
  `ended_at IS NULL` (no heartbeat freshness invented — OQ-04 stays closed).
  Both are raised as OQs for owner ratification; the payload stays
  authoritative so the mobile client never recomputes either number
  (MT-5.6-01 risk note).
- **Callers:** owner session 200; every agent role, a device token → 403
  `ROLE_NOT_PERMITTED`; anonymous → 401 `AUTH_REQUIRED` — all with the
  five-field Section 9.2 envelope. The deferred
  `/api/v1/dashboard/summary` entry in
  `tests/test_authorization_matrix.py::DEFERRED_ENDPOINTS` is retired per that
  drift guard's own instruction; the real per-caller cases (incl. the
  cross-project proof that a PID-scoped agent token receives no counts) live in
  `tests/test_dashboard_summary.py`.
- **Device cell is an OQ, not a widening:** §9.2 names Owner and §12.2 prints
  no dashboard row, so the mobile's device token is denied exactly like every
  other non-Owner caller. Granting the device a cell (the WP-1.8 checkpoints
  precedent) is an owner decision recorded as a follow-up.
- Tests: `backend/tests/test_dashboard_summary.py` (payload shape, six-key
  zero-fill, archive exclusion, velocity window, active-vs-ended sessions,
  full caller matrix + envelope codes).

### Follow-ups recorded by MT-1.15-06

- `schemas/openapi.yaml` regeneration for the new path — the audit finisher is
  the SOLE OpenAPI regenerator (Section 20.4 item 4); until it runs, the
  committed snapshot has no `/dashboard/summary` path and the mobile typed
  client stays on the hand-authored seam.
- Mobile swap of `DioDashboardSummarySource` to the generated client once the
  schema path lands (the WP-5.6 gap-note recommendation; one-file change
  behind the seam).
- OQ: the server's velocity definition/window (7-day rolling completions here)
  and the dashboard device cell — both await owner ratification.

---

**Thunderstorm pause:** paused at MT-1.15-01 (investigation only, no edits landed), remaining: MT-1.15-01/02/03 suites + changelog entries; MT-1.15-04/05 deferred per roadmap 4a.
