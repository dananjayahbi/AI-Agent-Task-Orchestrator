# Web Accessibility Audit — WP-4.11 (MT-4.11-03)

| Field | Value |
| --- | --- |
| Date | 2026-10-15 |
| Scope | Web app core flows: board (cards, filters, move), task modal (create/edit), review panel + decision dialogs, diff viewer, audit log, project forms (create/edit/policy), ops dashboard, app chrome |
| Themes | Light **and** dark (Section 13.4; next-themes token set from MT-4.1-04) |
| Standard | WCAG 2.1 AA (NFR-13) — SC 1.4.3 (text contrast 4.5:1), 1.4.11 (non-text/UI 3:1), 1.3.1 + 3.3.1 (labels & error association), 2.1.1 (keyboard, covered by MT-4.11-02) |
| Method | (1) computational contrast measurement of every shipped theme token and status-tone shade via the pure `web/lib/a11y/contrast.ts` pipeline (oklch → sRGB → WCAG luminance), parsed from `app/globals.css` so the audit checks the values that ship; (2) manual review of label wiring, accessible names and status-marker semantics across the component inventory in Section 13.2; (3) regression tests in `web/tests/a11y/` (35 tests) pinning every fixed finding in CI |

## Findings

| # | Surface | Finding | Measurement | Disposition |
| --- | --- | --- | --- | --- |
| 1 | Theme token (light) | `--ring` too light for a focus indicator | 2.59:1 on `--background` (needs 3:1, SC 1.4.11) | **Fixed** — darkened to `oklch(0.556 0 0)`: 4.73:1 on background, 4.34:1 on muted |
| 2 | Theme token (light) | `--muted-foreground` below AA on muted/secondary surfaces (chips, filter bar, banners) | 4.34:1 on `--muted` (needs 4.5:1) | **Fixed** — darkened to `oklch(0.53 0 0)`: 4.84:1 on muted, 5.28:1 on background |
| 3 | Theme token (dark) | `--destructive-foreground` near-white on the light-red `--destructive` (urgent priority chip, stalled/failed badges) | ~2.65:1 (needs 4.5:1) | **Fixed** — `oklch(0.205 0 0)` dark text: ~5.4:1 (mirrors the `--primary` dark pattern) |
| 4 | Theme token (light) | `text-destructive` on the shared `bg-destructive/10` tint (FormBanner errors) and `/15` badges | 4.17:1 (needs 4.5:1) | **Fixed** — `--destructive` darkened to `oklch(0.505 0.213 27.518)`: 5.48:1 on the /10 tint, 5.27:1 on /15 |
| 5 | Status tones | `text-emerald-600` "Pass"/"Yes"/exit-0/ops-OK on light surfaces | 3.77:1 | **Fixed** — `text-emerald-700` (5.48:1 on card, 4.94:1 on emerald tint); dark `emerald-400` kept (9.3:1) |
| 6 | Status tones | `text-amber-600`/`text-amber-700` warning tones on amber tints (ops alerts, stalled marker, paused badge) | 3.19:1 / 4.43:1 | **Fixed** — `text-amber-800` on tints (6.25:1); plain-background `lease-countdown` keeps `amber-700` (5.02:1) |
| 7 | Status tones | `text-red-600` critical ops badge on red tint | 4.17:1 | **Fixed** — `text-red-700` (5.59:1); dark `red-400` kept (6.5:1) |
| 8 | Audit log filters | Disabled contract-gated controls carried `opacity-60` on top of `muted-foreground`, pushing the text far below AA | ~2.6:1 effective | **Fixed** — `opacity-60` removed; the `disabled` attribute + `muted-foreground` (now 5.28:1) still convey the state, with `title` + contract note unchanged |
| 9 | Shared forms (`FieldRow`) | Validation errors (`role="alert"`) and hints were not programmatically associated with their inputs — a screen reader announced the error without linking it to the field | WCAG 1.3.1/3.3.1 | **Fixed** — `FieldRow` now emits `{id}-error` / `{id}-hint` and merges them into the control's `aria-describedby` (create/edit/policy/task forms all inherit) |
| 10 | Task form (description) | Markdown editor's own error message likewise unassociated | WCAG 3.3.1 | **Fixed** — textarea `aria-describedby="{id}-error"` when invalid |

### Verified clean (no fix needed)

* **Icon-only controls** — theme toggle, dialog close, card Move/Edit, chip clear, dependency/criterion/scope remove, attachment pick/remove, review-queue open: all carry `aria-label` or visible text (manual pass over `components/`).
* **Status markers** — priority chip (`aria-label="Priority …"` + text), stalled marker (text + title), merge-status badge (label + `data-merge-status`), diff file markers (`sr-only` label beside the glyph), rule table (text "Pass"/"Fail" + `data-passed`, never colour alone), ops alert badges ("Firing"/"OK"/"Unknown" text).
* **Form labels** — every audited field is a native label/control pair (`Label htmlFor` or wrapping `<label>`); tablists/tabs and toggle buttons expose `role`/`aria-selected`/`aria-pressed`.
* **Dark theme** — all dark-side pairs recomputed after the light fixes; foreground/muted/secondary on background/card/muted ≥ 5.8:1; chip foregrounds ≥ 5.4:1; ring ≥ 4.18:1.
* **Keyboard & focus visibility** — MT-4.11-02: global `:focus-visible` outline, component rings, focus trap/restore on dialogs, keyboard-only board move / create task / review decisions.

## Accepted limitations

None. Every finding above is fixed in code and pinned by regression tests; no core-flow contrast or label issue remains open (Section 19 WP-4.11 acceptance).

## Evidence

* `web/lib/a11y/contrast.ts` — pure oklch→sRGB→WCAG pipeline.
* `web/lib/a11y/theme-tokens.ts` — parses the shipped `app/globals.css`.
* `web/tests/a11y/contrast-labels.test.tsx` (20) — token pairs in both themes, status-tone shades, label associations, audit-filter controls.
* `web/tests/a11y/keyboard-navigation.test.tsx` (9) + `web/tests/a11y/roving.test.ts` (6) — MT-4.11-02 keyboard/focus suite.
