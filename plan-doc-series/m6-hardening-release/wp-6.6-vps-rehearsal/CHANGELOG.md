# WP-6.6 — VPS rehearsal: changelog

## Unreleased

- **Owner hosting decision (2026-10-15) — local-first, no VPS.**
  The owner confirmed the deployment target: run the full system on
  **this machine's Docker** (the PC is effectively always-on; the system is
  for personal use) and expose it for the mobile app through a
  **Cloudflare named tunnel** (`ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` is
  already present in the deployment env store; hostname still owner-open —
  OQ-11 convention `orchestrator.<owner-domain>`). The M0 compose stack
  already carries the `cloudflared` service for this.
  Consequence for this WP: the **VPS-provisioning wording of MT-6.6-01
  (and downstream MTs that assume a remote VPS) is superseded by owner
  decision** — the MTs stay not-done until they are formally re-scoped to
  a local-compose rehearsal (restore/backup/smoke legs are already proven
  locally by WP-6.2's drill and `docs/setup.md`'s dry run, but the WP-6.6
  acceptance as written targets a separate host). No work is claimed
  here; this entry records the decision only.
  Decision source: owner instruction 2026-10-15; surfaced in the
  `progress-status/I-want-from-the-user` action list.
