# What I need from you

**Status context:** 313/330 micro-tasks done (94.8%), everything code-side
finished. The 17 remaining items all need *you*. Local Docker + Cloudflare
hosting is recorded as the plan of record (no VPS), and the mimo/b.ai API is
already wired for visual descriptions (verified 200 on chat, `/v1/messages`
and vision before enabling; key lives **only** in the git-ignored
`infra/compose/.env` — nothing secret is in Git).

Reply with the numbered answers (e.g. "1: mydomain.com, 2: confirmed, 3: B…").
Each unchecked item blocks what is noted next to it.

---

## 1. Cloudflare tunnel — unblocks mobile access + MT-5.1-04 ⬜

- [ ] **Give me the public hostname** you want for the system.
      Convention: `orchestrator.<your-domain>` (OQ-11). I will wire the DNS
      route + env from it.
- [ ] **Confirm the tunnel token** already in `infra/compose/.env`
      (`ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN`) is a **named tunnel** token
      from Cloudflare Zero Trust → Networks → Tunnels — not an old
      quick-tunnel token. If unsure, paste a fresh one.
- [ ] If you own the domain on Cloudflare, either leave me access to create
      the CNAME (`orchestrator.<domain>` → `<tunnel-id>.cfargotunnel.com`)
      or create that record yourself and tell me when it is live.

*Why:* the mobile app + the 30-minute through-tunnel verification run
(MT-5.1-04, OQ-11) cannot happen until this hostname exists.

## 2. Push notifications — unblocks the one-real-push test (MT-5.10-05) ⬜

- [ ] **Create (or pick) a Firebase project** and download a **service
      account JSON** with FCM permissions. Hand me the project ID + JSON —
      I will store them as `ORCHESTRATOR_FCM_PROJECT_ID` /
      `ORCHESTRATOR_FCM_CREDENTIALS_JSON` in the git-ignored env only and
      flip `ORCHESTRATOR_PUSH_ENABLED=true`.
- [ ] **Install the signed release APK on your Android phone**
      (`app-prod-release.apk`, sideload steps in `mobile/docs/distribution.md`)
      and keep the phone on the same network as the tunnel URL.

*Why:* the whole push chain (sender → FCM → device) is code-complete but
has never delivered a real notification; the checklist for the run is at
`mobile/docs/release-checklist.md`.

## 3. Agent client-compatibility matrix — unblocks MT-6.5-02/03 ⬜

Pick ONE:

- [ ] **A) Give me access** for the clients you actually care about — any of:
      Claude Code, GitHub Copilot CLI, OpenCode, aider, DeepSeek (API key
      or logged-in session as each requires). Name which ones.
- [ ] **B) Accept the gap:** permanently defer the matrix (personal use).
      MT-2.11-02..07 *and* MT-6.5-02/03/04 then stay open-by-owner-acceptance
      forever, recorded as such. After B, the only runnable remaining work
      is WP-6.6 re-scoped to local (item 5).

## 4. iOS — optional ⬜

- [ ] Apple Developer account (≈$99/year) **if** you want TestFlight/iOS
      builds; otherwise confirm **Android-only** and MT-5.10-03 stays
      permanently deferred (already recorded).

## 5. Confirm the two decisions I recorded on your behalf ⬜

- [ ] **WP-6.6 re-scope:** you said "local Docker instead of a VPS" — I
      recorded that in `plan-doc-series/m6-hardening-release/wp-6.6-vps-rehearsal/CHANGELOG.md`
      as superseding the VPS wording of MT-6.6-01. Confirm you want the
      formal re-scope (local-compose rehearsal: backup/restore/smoke against
      this machine) — then I dispatch it as the final batch.
- [ ] **Always-on host hygiene:** enable Docker Desktop auto-start and
      Windows Update auto-restart-with-active-hours? (Recommended for a
      personal always-on box; you decide — I can walk you through it.)

## 6. LLM API key hygiene (mimo-v2.6-flash / b.ai) ⬜

- [ ] **Consider rotating the key** later: it passed through this chat, so
      treat it as mildly exposed. When you do, give me the replacement and I
      will update only the one git-ignored env line.
- [ ] **Usage posture (already applied, flag any objection):** the key is
      used only by the attachment description provider — cache-first,
      generated once per image, cost/failures logged, timeouts at 30s. I
      made 4 tiny probe calls while verifying; nothing else calls the API
      without your say-so.

## 7. Backup destination ⬜

- [ ] **Confirm or change the backup host directory.** Default is the
      git-ignored `infra/compose/backup-data/` (same disk as the system).
      For a personal deployment, point `ORCHESTRATOR_BACKUP_HOST_DIR` at a
      drive/location you actually back up (external disk, NAS), or tell me
      to leave it local.
- [ ] Optional: a second machine or cloud copy for the weekly backup
      artifact — WP-6.2 proves the dump/restore path locally
      (`docs/plan/wp-6.2-restore-drill-2026-10-14.md`), but off-machine
      retention is currently your job.

---

### Fastest path to "100%"

1. Answer **1** (hostname/token) → I finish the tunnel leg (MT-5.1-04).
2. Answer **2** (Firebase + phone) → I run the real push preflight
   (MT-5.10-05) and close WP-5.10.
3. Answer **3B** or provide clients → closes or accepts the matrix.
4. Confirm **5** → I dispatch the final local-rehearsal batch (WP-6.6).
5. Items 4/6/7 are optional hygiene — do them at your pace.
