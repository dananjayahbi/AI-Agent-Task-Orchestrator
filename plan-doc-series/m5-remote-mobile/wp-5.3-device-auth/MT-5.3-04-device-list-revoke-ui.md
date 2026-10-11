# MT-5.3-04 — Implement Device List and Revoke UI in Web Account Settings

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.3-04 |
| Title | Implement device list and revoke UI in web account settings |
| Parent WP | WP-5.3 — Device registration and mobile authentication (Milestone M5) |
| Requirements | FR-SEC-02, FR-MOB-06 |
| Priority | M |
| Dependencies | MT-5.3-03 (revocation endpoint behavior) |
| Parent sections | 13.1, 13.3, 19.1 (WP-5.3), ADR-006, 20.4, 20.5 |

## Context
Section 13.1: the Account settings route contains "Password, devices (list and
revoke), notification preferences." Section 19 (WP-5.3) deliverable: "revoke from
web UI." This task builds the Owner-facing surface that lists registered devices and
triggers `DELETE /devices/{id}` (MT-5.3-03), completing the lost-phone mitigation of
Section 12.1.

## Inputs / Prerequisites
* MT-5.3-03 — revocation endpoint with immediate-rejection semantics.
* Section 9.2 — `DELETE /devices/{id}` exists; **`GET /devices` does not** — the
  list half depends on the OQ raised in MT-5.3-01 (see risk notes) being resolved
  and the Section 9.2 amendment landing first.
* WP-4.x web foundations — Next.js app, generated typed API client from the OpenAPI
  schema (Section 13.3), error-code-to-message mapping (Section 13.3).
* Section 13.1 — the account settings route and its contents.

## Scope (in)
* The Account settings page section listing the Owner's devices (name/metadata,
  registration/recency fields available from the API, current-session indication if
  provided) with a revoke control per device.
* Revoke action wired to `DELETE /devices/{id}` with an explicit confirmation (this
  cuts off a phone in use — see Section 14.2's approve-safety spirit for confirm
  patterns), success/error states mapped from canonical error codes
  (Section 13.3).
* List state handling per Section 13 conventions: loading, empty ("no devices"),
  and error states as separate concerns (Section 20.3 UI splitting rule).
* Generated API client usage only — no hand-rolled fetch (Section 13.3,
  NFR-11 schema-driven client).
* Widget/component tests: renders the list, revoke flow calls the endpoint with
  confirmation, error mapping, empty state.

## Out of scope
* Backend endpoints — MT-5.3-01/03 (and the OQ-driven list endpoint).
* Password change UI (the same settings route hosts it) — WP-4.x/WP-1.2 scope.
* Notification preferences (same route) — WP-5.4.
* Mobile app settings (device info screen, Section 14.1) — WP-5.x Flutter work.
* Styling system/theme work — web design-system WP.

## Target paths
* `web/` — account settings route/components (device list + revoke control)
* `web/` component tests for the device settings section
* WP changelog entry

## Acceptance criteria
- [ ] The Account settings page lists the Owner's registered devices per
  Section 13.1, using the generated API client (Section 13.3).
- [ ] Revoking a device from the UI triggers `DELETE /devices/{id}` after
  confirmation and reflects the result; errors map from canonical codes to friendly
  messages (Section 13.3; Section 20.4 item 5).
- [ ] Loading, empty and error states exist as distinct states (Section 20.3 UI
  splitting rule).
- [ ] Public contract usage matches the OpenAPI schema — no ad-hoc payloads
  (Section 20.4 item 4).
- [ ] Component tests green in CI (item 2); changelog note added (item 7).

## Test command
`npm run test -- --filter web` (or the web package's configured component-test
command) covering: list rendering, revoke-with-confirmation flow, canonical error
mapping, and the empty state.

## Attachments
* [Section 13.1 — Web information architecture (Account settings)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.3 — Data and state handling](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-5.3 deliverables (revoke from web UI)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* **Blocking dependency:** Section 9.2 has no `GET /devices` listing endpoint, so the
  list half cannot be built without first amending the parent plan (new OQ, next
  free `OQ-15+` id: "add GET /devices to Section 9.2?"). Either sequence this MT
  after that amendment, or split: revoke-only UI first, list when the endpoint
  lands — record the decision; do not invent an undocumented endpoint.
* Revoking the Owner's *current* session's device (or the only device) mid-use is a
  UX edge the plan does not address — handle gracefully (disable the control for the
  active device or confirm strongly) and note the choice in the changelog.
