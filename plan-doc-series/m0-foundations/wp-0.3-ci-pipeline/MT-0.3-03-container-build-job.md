# MT-0.3-03 — Add Container Build Job

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.3-03 |
| Title | Add container build job |
| Parent WP | WP-0.3 — CI pipeline (Milestone M0) |
| Requirements | NFR-07, NFR-11 |
| Priority | M |
| Dependencies | MT-0.2-01 (placeholder images), MT-0.3-01 |
| Parent sections | 16.1, 18, 19.1 (WP-0.3), 20.4 |

## Context
Section 18 lists "container build" among the blocking CI quality gates, and WP-0.3's
deliverables include a container build job. The Compose stack (MT-0.2-01) already
refers to backend and web images; this task ensures CI builds every image definition
in the repository on each PR, so a broken Dockerfile or base-image change blocks merge
from day one.

## Inputs / Prerequisites
* MT-0.2-01 — Compose services referencing placeholder `backend` and `web` images.
* MT-0.3-01 — the CI workflow to extend.
* Parent plan Section 16.1 — image basis column (backend image, Next.js image; official
  images for postgres/redis/cloudflared are pulled, not built).
* Parent plan Section 18 — quality gates include container build.
* Dockerfiles for the skeleton images (placeholder backend/web image definitions from
  WP-0.2).

## Scope (in)
* Add a CI job that discovers and builds every Dockerfile/image definition in the
  repository (initially the placeholder `backend` and `web` images).
* Fail the job on any build error, with clear log attribution to the failing image.
* Keep the job generic so images added later (real backend image in WP-1.1, real web
  image in WP-4.1, worker/beat reuse of the backend image) are picked up without
  rewriting the job.
* Make the job a required check so a failed build blocks merge.
* Add a WP changelog note.

## Out of scope
* Pushing images to a registry — not required for the M0 skeleton (release/registry
  concerns belong to M6).
* Pinning `prod` image digests — profile concern of MT-0.2-02 (recorded there).
* Building bridge packages as containers — the bridge is a host-side Python package
  (Section 10.11), not a Compose service.
* Vulnerability scanning of built images — MT-0.3-04 dependency scanning covers the
  dependency dimension; image CVE scanning belongs to M6 hardening.

## Target paths
* `.github/workflows/` — container build job in the CI workflow
* Placeholder Dockerfiles for `backend` and `web` if not already defined by WP-0.2
* WP changelog entry

## Acceptance criteria
- [ ] A container-build job exists and builds every image defined in the repository.
- [ ] The job passes on the current skeleton (placeholder backend/web images build).
- [ ] A broken Dockerfile makes the job fail, and as a required check it blocks merge
  (WP-0.3 acceptance).
- [ ] Job requires no registry credentials and commits no secrets (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the workflow on a branch and confirm the container-build job reports success for
all images (e.g. `gh run view --log` shows each image built); optionally break a
Dockerfile on a throwaway branch to confirm the job fails and merge is blocked, then
revert.

## Attachments
* [Section 16.1 — Compose services](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Image definitions are split across milestones (placeholders in WP-0.2, real backend
  image in WP-1.1) — a hardcoded image list would silently skip future images; keep
  discovery pattern-based.
* Build on untrusted PRs must not receive secrets (NFR-07): run build-only, no push,
  no privileged secrets.
