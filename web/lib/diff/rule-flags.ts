'use client';

/**
 * Rule-flag extraction (MT-4.7-05; Section 13.2 "jump to files
 * flagged by rule results"; Section 9.4 authority note; Section 20.5).
 *
 * Reads the Audit Report's persisted `policy_rule_results`
 * (Section 7.2) and maps **file-based** rule failures (R2 scope, R3
 * critical paths, R4 migrations, R5 sensitive config — the Section
 * 9.4 table rows whose fail conditions are file matches) to the file
 * paths the backend flagged. The engine is authoritative: this module
 * never re-evaluates rules and never re-matches globs client-side —
 * it renders exactly what was persisted.
 *
 * Shape discipline (MT-4.7-05 risk note; Section 20.5 — no invented
 * contract): WP-3.4's engine persists one row per rule
 * `{rule, passed, review_reason}` (its changelog fixes the shape).
 * Rows may additionally carry a file payload (`files: string[]`)
 * when the engine records which files triggered a file-based rule;
 * this module reads that payload **if present** and otherwise marks
 * nothing for the row — an unknown or absent shape is "no markers",
 * never a guess. Non-file rules (R1, R6–R9) never produce file
 * markers even if a payload rides along — they belong to the review
 * panel's rule table (WP-4.8), not the diff viewer.
 *
 * Multiple rules may flag the same file: the marker carries **all**
 * flagging rule ids (Section 9.4's stated purpose — the reviewer sees
 * exactly why the task was escalated).
 */
import { FILE_BASED_RULES, type RuleId } from '@/lib/diff/rules';

/** File path → the flagging rule ids, verbatim from the persisted rows. */
export type FlaggedFiles = Map<string, RuleId[]>;

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === 'string');
}

/**
 * Extract flagged files from a `policy_rule_results` blob. Tolerant
 * by design: `null` (pre-engine report), a non-list, or malformed
 * rows all degrade to an empty map — no markers, no errors
 * (Sections 8.5, 9.4; MT risk note).
 */
export function extractFlaggedFiles(policyRuleResults: unknown): FlaggedFiles {
  const flagged: FlaggedFiles = new Map();
  if (!Array.isArray(policyRuleResults)) return flagged;

  for (const row of policyRuleResults) {
    if (typeof row !== 'object' || row === null) continue;
    const candidate = row as Record<string, unknown>;
    const rule = candidate['rule'];
    if (typeof rule !== 'string' || !(FILE_BASED_RULES as readonly string[]).includes(rule)) {
      continue; // non-file rule (or malformed) — never a file marker
    }
    if (candidate['passed'] !== false) continue; // only failures flag files
    const files = candidate['files'];
    if (!isStringArray(files)) continue; // no file payload → no markers (no guessing)
    for (const path of files) {
      if (path === '') continue;
      const rules = flagged.get(path);
      if (rules === undefined) flagged.set(path, [rule as RuleId]);
      else if (!rules.includes(rule as RuleId)) rules.push(rule as RuleId);
    }
  }
  return flagged;
}

/** The rule ids flagging one path (empty array when unflagged). */
export function rulesForPath(flags: FlaggedFiles, path: string): RuleId[] {
  return flags.get(path) ?? [];
}
