# MT-6.1-02 — Test Upload Abuse Cases (Traversal, Oversized, Spoofed MIME)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.1-02 |
| Title | Test upload abuse cases (traversal, oversized, spoofed MIME) |
| Parent WP | WP-6.1 — Security review (Milestone M6) |
| Requirements | NFR-07, FR-ATT-01 |
| Priority | M |
| Dependencies | MT-1.11-02 (upload validation), MT-1.11-03 (multipart endpoint), MT-1.12-01 (type detection), MT-6.1-01 (findings log and severity scale established) |
| Parent sections | 12.1 (malicious uploads threat), 12.3 (path and scope enforcement), 18 (Security row: path traversal, upload abuse; Integration row: scrambled and oversized inputs), 19 (WP-6.1 acceptance), 20.4, 20.5 |

## Context
Section 12.1's "Malicious uploads" threat lists the mitigations: type sniffing, size
limits, sandboxed parsing in the worker, optional AV. Section 12.3 adds the path
enforcement: payload paths normalized and rejected if they escape the repo root
(traversal, symlink, absolute). Section 18 puts "path traversal" and "upload abuse"
in the Security row and "scrambled and oversized inputs" in the Integration row —
and WP-6.1's acceptance specifically requires **traversal tests in CI**. This slice
attacks the attachment intake (WP-1.11/WP-1.12) with the abuse cases and turns the
results into CI-enforced tests plus findings-log entries.

## Inputs / Prerequisites
* MT-1.11-02 — upload validation (size/type limits per FR-ATT-01) and MT-1.11-03 —
  the multipart upload endpoint as deployed.
* MT-1.12-01 — content-based type detection (the "type sniffing" mitigation of
  Section 12.1).
* Parent plan Section 12.3 — normalization rules the path tests must mirror
  (traversal, symlink, absolute rejected; `target_scope` globs validated on
  creation).
* Parent plan Section 12.1 — malicious uploads threat and the worker-sandbox
  mitigation note.
* MT-6.1-01 — findings log, severity scale and threat-to-test mapping to update.
* Local Compose stack with an authenticated owner fixture and storage volume.

## Scope (in)
* Abuse-case tests against the upload endpoint, each asserting a canonical Section
  9.2 error (code exists in the catalog — Section 20.4 item 5) and no write outside
  the storage root:
  * **Traversal:** filenames/paths containing `../` segments, encoded traversal,
    absolute paths, and symlink-style names attempting to escape the content-addressed
    storage (Section 12.3).
  * **Oversized:** bodies beyond the configured size limit rejected cleanly at the
    endpoint, without partial artifacts left behind (FR-ATT-01 size limits;
    Section 18 oversized inputs).
  * **Spoofed MIME:** content whose declared type differs from its bytes (e.g. an
    executable renamed to an image extension, an image renamed to a document)
    rejected or quarantined by sniffing, never trusted from the client header
    (Section 12.1 type sniffing; Section 18 scrambled inputs).
* A worker-side check per Section 12.1: parsing runs in the worker process (not the
  web process) — assert the separation exists as designed (by configuration/process
  wiring), noting that OS-level sandboxing is explicitly post-v1 (Section 12.3
  limitation recorded in the mapping).
* Append results to the threat-to-test mapping (malicious-unupload rows now point at
  these tests) and any findings to the findings log with severity; fix
  high/critical gaps in validation here when small, else file follow-ups.
* Changelog note (Section 20.4 item 7).

## Out of scope
* The other review slices — MT-6.1-01/03/04/05 (shared findings log only).
* Implementing new validation — WP-1.11 already delivered it; this task verifies
  and, where a gap is found, fixes or files it.
* Optional antivirus integration (Section 12.1 "optional AV") — not a v1
  requirement; note its absence in the mapping rather than building it.
* OS-level sandboxing/containers for workers — explicitly post-v1 (Section 12.3).

## Target paths
* `backend/tests/` — upload abuse test suite (traversal, oversized, spoofed MIME)
* `docs/plan/security-threat-test-mapping.md` (rows updated with these tests)
* `docs/plan/security-findings-log.md` (findings appended)
* WP changelog entry

## Acceptance criteria
- [ ] Traversal cases (raw, encoded, absolute, symlink-style) are rejected and the
  tests run in CI — Section 19 WP-6.1 acceptance "traversal tests in CI".
- [ ] Oversized uploads are rejected with a canonical error and no partial artifact
  persists (FR-ATT-01; Section 9.2 catalog discipline).
- [ ] Spoofed-MIME cases are caught by content sniffing, never by the client
  declared type alone (Section 12.1).
- [ ] Worker-vs-web parsing separation verified as designed, with the OS-sandbox
  limitation recorded (Sections 12.1, 12.3).
- [ ] Threat-to-test mapping updated; findings logged with severity; zero open
  critical/high from this slice (Section 19 WP-6.1 acceptance).
- [ ] Tests green in CI (Section 20.4 item 2); changelog note added (item 7).

## Test command
`pytest backend/tests/ -k upload_abuse -v` — all traversal, oversized and
spoofed-MIME cases pass with canonical errors; then confirm
`docs/plan/security-threat-test-mapping.md` references these tests and the findings
log has no open critical/high entries from this slice.

## Attachments
* [Section 12.1 — Threat model (malicious uploads)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.3 — Path and scope enforcement](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.1 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Abuse fixtures must be inert (fake/malformed content) — this suite proves
  rejection behavior; never commit real weaponized samples (Section 20.4 item 3
  spirit; keep fixtures generated or trivially synthetic).
* Storage-root assertions depend on the storage abstraction (WP-1.11-01): if the
  S3-compatible configuration is in play, the traversal boundary moves to key
  prefixes — test both configuration modes or record which was covered.
* "No partial artifact" can fail at the storage layer rather than validation — if
  cleanup gaps surface, log as a finding with severity; do not weaken the assertion
  to make CI green.
