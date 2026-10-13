# WP-3.1 — Policy model: glob fields & presets

## Unreleased

### MT-3.1-01 — Policy fields and defaults (verify/backfill)

Verified the Section 7.2 Project Policy table against WP-1.3's existing
implementation: **all 15 fields** the plan table enumerates persist with
their literal defaults, the `GET/PATCH /projects/{pid}/policy` endpoint
round-trips the full table, and no migration or data fix-up was needed —
WP-1.3's migration `0002_initial` already created the three glob fields
with the concrete default lists, so projects created before this task
carry the same defaults (locked by
`tests/test_project_policy_fields.py::test_backfilled_rows_render_the_same_defaults`).
`lease_extension_mode` stays `checkpoint_only` as the enforced default;
`GET` still renders exactly the Section 7.2 field set.

Decision (deviation note): MT-3.1-01's text says "16 fields" while the
plan's Section 7.2 table — the stated source of truth — lists **15**
rows (and WP-1.3's changelog recorded 15). Implemented the table
verbatim; the count discrepancy is recorded here rather than resolved
by inventing a field. Open question for the plan owner if a 16th field
was intended.

New test file: `backend/tests/test_project_policy_fields.py` (runs under
the MT command `-k project_policy` together with WP-1.3's suite).

### MT-3.1-02 — Framework preset library

New data module `backend/apps/projects/policy_presets.py`: a versioned
(`PRESET_LIBRARY_VERSION = 1`), read-only registry of framework presets
supplying the three Section 7.2 glob lists. Three presets ship:
**django**, **nextjs**, **flutter** — each derived from the plan's
category meanings (CI/CD + root migrations + security config → critical;
framework migration directories → migration; env files + key material +
security rules → sensitive) with the derivation documented next to the
data (Section 20.1 item 5 — no hidden decisions; owner confirmation
flagged below).

Hard-rule compliance:

* **presets are data, not code branches** — selection is an input
  (`policy_preset`) the serializers expand into the three glob fields;
  nothing in the runtime branches on framework;
* **blast radius** — a preset writes *only* `critical_path_globs`,
  `migration_path_globs`, `sensitive_config_globs`; every other policy
  field keeps its Section 7.2 default;
* **preset globs must pass the validator** — enforced twice:
  `preset_glob_fields()` runs the Section 12.3 validator on every apply
  (runtime guard), and `tests/test_policy_presets.py` +
  `tests/test_policy_validation.py` assert it for the shipped data.

Selection surfaces (Section 19's "selectable at project creation"):

* `POST /projects` gains optional `policy_preset` (Owner-only route;
  unknown ids → catalog `VALIDATION_ERROR` with `policy_preset` in
  `details`); `create_project()` applies the preset inside the creating
  transaction and records the id in the `project.created` event's
  `data` (audit trail, Section 12.5);
* `PATCH /projects/{pid}/policy` gains the write-only `policy_preset`:
  apply a preset in one action. Combining it with any explicit glob
  field in one request is **refused** (conflict rule — no implicit
  ordering between preset and explicit lists). The field is write-only:
  `GET` keeps rendering exactly the Section 7.2 field set.

DTO listing surface: `PolicyPresetSerializer` + `render_presets()` in
`apps/projects/serializers/policy.py` render the whole library (no new
route — see follow-ups). Preset ids are stable API values; content
changes bump `PRESET_LIBRARY_VERSION`.

New test file: `backend/tests/test_policy_presets.py` (`-k policy_presets`).

### MT-3.1-03 — Policy validation (Section 12.3 glob discipline)

New module `backend/apps/projects/services/globs.py` — **the single
shared matcher** (MT risk note; WP-3.4 must import from here):

* `glob_to_regex()` — one translation: `*` = one segment, `**` = whole
  segment recursive operator only, `?` = one char, `[...]` classes;
  unparseable syntax (`**` misuse, unterminated class) is a `ValueError`,
  surfaced to clients as a per-entry problem — a glob the engine could
  never evaluate is rejected at the boundary, never silently
  non-matching;
* `glob_matches()` — anchored full-path match (WP-3.4's R3/R4/R5 reuse
  target; `test_policy_validation.py` locks the semantics);
* `validate_glob_list()` — Section 12.3 rules: max 64 entries / 500
  chars, forward slashes only, no NUL, repo-root relative (no leading
  `/`, no `X:` drive), no `..` segments, parseable syntax; errors are
  per-index under the field name, raised as DRF `ValidationError` →
  catalog `VALIDATION_ERROR`.

Wired into `ProjectPolicySerializer` for the three glob fields (field
validators call it without the field key so DRF's own field wrapping
produces `{field: {index: [problems]}}` exactly once — the shape the
target-scope validator in `apps.tasks` already established). Cross-field
rule added: `lease_max_total_minutes >= lease_duration_minutes` on the
*merged* partial view (an absent side takes the instance value), so
patching one side alone can never land an invalid combination. Existing
bounds (positive integers, `auditor_min_confidence` 1–5,
`max_concurrent_tasks` >= 0 per G-26) and closed enums are unchanged;
the stock defaults and every preset payload pass the endpoint's own
validation (locked by tests).

New test file: `backend/tests/test_policy_validation.py`
(`-k policy_validation`).

### Risk notes / follow-ups

* **OpenAPI drift** — the two new optional request fields
  (`policy_preset` on create and on policy PATCH) change the generated
  schema. `schemas/openapi.yaml` was **not** regenerated here: that file
  is owned by the concurrent WP-3.x openapi agent this round. Follow-up:
  regen (`manage.py spectacular`) so the CI snapshot gate passes.
* **Authorization matrix** — no new routes were added (the preset
  listing is a DTO, not an endpoint), so no new matrix rows are needed;
  the existing Owner rows cover `POST /projects` and policy `PATCH`.
  If a preset-list endpoint is ever added, the matrix editor must add
  its row (planning note, see OQ below).
* **Sibling validator consolidation** —
  `apps.tasks.services.tasks.validate_target_scope_globs` carries the
  identical Section 12.3 rules; folding it onto
  `services/globs.validate_glob_list` is a noted follow-up (out of
  WP-3.1 scope; behavior kept identical on purpose).
* **Owner confirmation** — the concrete preset globs are documented,
  conservative translations of the plan's prose categories (Section
  20.1 item 5); flag for owner review before WP-3.4 matches against
  them in anger.
* **OQ** — Section 7.2's bounds beyond the stated ranges (e.g. an upper
  limit on `lease_max_total_minutes`) were *not* invented; if the plan
  owner wants caps, they land as a follow-up. `merge_strategy` keeps
  exactly the three plan values (a `manual` strategy surfacing in
  WP-3.7 would be an OQ then).
