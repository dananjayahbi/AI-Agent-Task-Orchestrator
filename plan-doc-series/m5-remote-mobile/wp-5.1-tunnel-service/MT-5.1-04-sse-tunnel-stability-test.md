# MT-5.1-04 — Verify SSE Stability Through the Tunnel (30 min Idle Test)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.1-04 |
| Title | Verify SSE stability through the tunnel (30 min idle test) |
| Parent WP | WP-5.1 — `cloudflared` service and tunnel ingress (Milestone M5) |
| Requirements | FR-NET-01, FR-NET-02, NFR-03, NFR-04, ADR-002 |
| Priority | M |
| Dependencies | MT-5.1-02 (ingress); WP-1.10 complete (SSE stream endpoint); WP-1.9 (events) |
| Parent sections | 9.6, 15.1, 15.4, 19 (WP-5.1), 20.4, 20.5 |

## Context
WP-5.1's acceptance: "no inbound ports required; SSE stays connected for at least 30
minutes idle with heartbeats." Section 15.4 requires exactly this verification:
"SSE through the tunnel needs verified idle timeouts and no response buffering; the
15 s heartbeat is designed for this (verify in WP-5.1)." ADR-002 chose SSE partly
because it is proxy-friendly and resumable by event id — the tunnel is the
load-bearing proof of that claim: if Cloudflare's edge or the origin buffers or
drops idle streams, the realtime board (web) and mobile live feeds break silently.

## Inputs / Prerequisites
* MT-5.1-02 — ingress mapping routes the tunnel hostname to `backend`, including the
  unbuffered events path.
* WP-1.10 — `GET /events/stream` (SSE) with per-event authorization, heartbeat
  comments every 15 s and resume via last event id (Section 9.6); WP-1.9 — event
  history for resume checks.
* Parent plan Section 9.6 — stream contract (filters, heartbeat, lossless resume);
  Section 15.4 — the verification obligation.
* A reachable tunnel hostname (operator-provisioned per OQ-11 / MT-5.1-03) and an
  Owner session to authorize the stream.
* A client able to hold a 30-minute connection (scripted client preferred for
  repeatability; e2e home per Appendix A).

## Scope (in)
* Execute and record the 30-minute idle test through the tunnel hostname: open an
  authorized `GET /events/stream` connection, stay idle (no published events) for at
  least 30 minutes, and assert the connection survives — heartbeat comments (every
  15 s, Section 9.6) keep it alive with zero disconnects, zero proxy timeouts.
* Assert no response buffering: publish one event near the end of the idle window
  and confirm it arrives promptly (not held until stream end) — measure and record
  delivery latency against NFR-03's expectations for local/tunnel paths.
* Assert lossless resume through the tunnel: drop the connection deliberately,
  reconnect with the last event id, and confirm missed events replay with no gaps
  and no duplicates (Section 9.6, NFR-04 no-lost-state discipline).
* Repeat the idle cycle at least once to show stability is not a one-off; record
  results (timestamps, disconnect count, latency) in the verification notes.
* If any assertion fails, capture evidence (client logs, cloudflared logs, any
  buffering/timeout signatures) and file the fix against MT-5.1-02's ingress or an
  OQ — do not weaken the acceptance bar.
* Add a WP changelog note with the verification result.

## Out of scope
* The stream endpoint implementation and its LAN tests — WP-1.10.
* Twenty-agent load and p95 fan-out numbers — Section 18 performance layer,
  WP-6.3.
* Mobile client's SSE consumption — WP-5.5 (later, reuses these notes).
* Edge Access policy interaction with the stream — WP-5.2.
* Long-term monitoring/alerting of stream health — WP-6.4.

## Target paths
* `e2e/` (scripted tunnel SSE verification scenario, if scripted)
* `infra/cloudflare/` (verification notes: date, results, evidence)
* WP changelog entry

## Acceptance criteria
- [ ] An SSE connection through the tunnel hostname stays connected for at least 30
  minutes idle with 15 s heartbeats and zero disconnects (WP-5.1 acceptance;
  Section 15.4).
- [ ] A published event is delivered during/after the idle window without buffering
  artifacts (Section 15.4 "no response buffering"; ADR-002).
- [ ] Reconnect with last event id through the tunnel yields no gaps and no
  duplicates (Section 9.6 lossless resume; NFR-04).
- [ ] The test uses the tunnel hostname end-to-end with no inbound ports involved
  (FR-NET-01) — LAN control run documented for comparison.
- [ ] Verification notes with evidence are committed; changelog note added
  (Section 20.4 item 7).
- [ ] CI remains green — the 30-minute test runs on demand/nightly, not on every PR
  (documented invocation; Section 20.4 item 2).

## Test command
Run the tunnel SSE scenario against the provisioned hostname (e.g. the e2e script
from `e2e/` targeting `GET /events/stream` via the tunnel URL) for ≥ 30 minutes
idle, then a disconnect/resume cycle; confirm zero drops, prompt single-event
delivery and gap-free replay in the recorded output; re-run once for stability.

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 15.4 — Operational details (SSE through the tunnel)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The test depends on live Cloudflare edge behavior that CI cannot fully own —
  keep the scripted scenario reproducible and record the date/edge conditions in the
  notes; a failure caused by external changes is still a WP-5.1 acceptance
  failure until understood (raise an OQ with evidence).
* Cloudflare's Free plan idle timeouts are the exact risk this test exists to
  measure — if 30 minutes fails, the fix (heartbeat interval vs edge limits vs
  ingress buffering) must be derived from evidence in Section 15.4's terms, not by
  shortening the acceptance criterion.
* Authorization expiry can masquerade as a tunnel drop — align the Owner session
  lifetime with the 30-minute window (or re-auth inside the test) so failures are
  attributable; session-lifetime values come from Section 9.10, not invented here.
