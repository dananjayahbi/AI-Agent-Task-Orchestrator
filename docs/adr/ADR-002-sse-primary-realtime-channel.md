# ADR-002 — SSE as the primary realtime channel

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-002 (embodies decided OQ-01) |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

The web board and mobile client need live updates of every state change, and the stack
sits behind a Cloudflare tunnel where connection behavior matters (Sections 6.2, 9.6).
OQ-01 asked whether SSE alone or WebSocket as well would be the v1 transport; the
review session decided SSE-only for v1 on 2026-10-11.

## Decision

SSE as the primary realtime channel.

## Rationale

One-way feeds, resumable by event id, proxy-friendly.

## Alternatives considered

* WebSocket via Channels.

## Consequences

* Reconnecting clients send their last event id and receive missed events with no
  gaps and no duplicates, then switch to live (Section 9.6).
* Heartbeat comments keep tunnel and mobile connections alive (Section 9.6).
* No bidirectional channel ships in v1: OQ-01 is revisited only if a future
  requirement for bidirectional streaming appears.
* Django Channels is not required for realtime fan-out; Redis carries the published
  events (Sections 6.3, 9.6).

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
