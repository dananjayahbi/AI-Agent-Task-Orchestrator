/**
 * Policy rule-table vocabulary (MT-4.8-02; Section 9.4's R1–R9 table,
 * Section 13.2 "rule table", Section 20.5 verbatim-discipline).
 *
 * Presentation only: the Audit Report's persisted `policy_rule_results`
 * rows (`{rule, passed, review_reason}` — WP-3.4's changelog shape) are
 * rendered as stored; this module supplies the Section 9.4 label per rule
 * id and the fail-reason mapping a failing row falls back to when the row
 * itself carries no `review_reason`. Nothing is ever re-evaluated
 * client-side (Section 9.4 authority note — the engine is authoritative).
 */
import type { ReviewReason } from '@/lib/review/review-reasons';

/** One Section 9.4 rule definition: id → human label + fail review reason. */
export type RuleDefinition = {
  id: string;
  label: string;
  reviewReason: ReviewReason;
};

/** Section 9.4's table in plan order — every R1–R9 row. */
export const POLICY_RULES: readonly RuleDefinition[] = [
  { id: 'R1', label: 'Tests', reviewReason: 'test_failure' },
  { id: 'R2', label: 'Scope', reviewReason: 'scope_violation' },
  { id: 'R3', label: 'Critical paths', reviewReason: 'critical_path_changed' },
  { id: 'R4', label: 'Migrations', reviewReason: 'migration_detected' },
  { id: 'R5', label: 'Sensitive config', reviewReason: 'sensitive_config_changed' },
  { id: 'R6', label: 'Diff size', reviewReason: 'diff_over_threshold' },
  { id: 'R7', label: 'Confidence', reviewReason: 'low_confidence' },
  { id: 'R8', label: 'Auditor flag', reviewReason: 'auditor_flagged' },
  { id: 'R9', label: 'Switch', reviewReason: 'policy_forced_review' },
];

const RULE_BY_ID = new Map(POLICY_RULES.map((rule) => [rule.id, rule]));

/** One persisted rule row, normalized for rendering. */
export type RuleTableRow = {
  /** The rule id verbatim from the persisted row. */
  rule: string;
  passed: boolean;
  /** The row's own persisted `review_reason` when present (verbatim). */
  persistedReason: string | null;
  /** Section 9.4's fail-reason mapping for known ids (null for unknown ids). */
  mappedReason: ReviewReason | null;
  /** Section 9.4 label for known ids (null → render the id verbatim only). */
  label: string | null;
};

function normalizeRow(entry: unknown): RuleTableRow | null {
  if (typeof entry !== 'object' || entry === null) return null;
  const candidate = entry as Record<string, unknown>;
  const rule = candidate['rule'];
  const passed = candidate['passed'];
  // Tolerant by design: a row without a string id or a boolean outcome is
  // malformed — drop it rather than invent an outcome (Section 20.5).
  if (typeof rule !== 'string' || rule === '' || typeof passed !== 'boolean') return null;
  const reason = candidate['review_reason'];
  const definition = RULE_BY_ID.get(rule);
  return {
    rule,
    passed,
    persistedReason: typeof reason === 'string' && reason !== '' ? reason : null,
    mappedReason: definition?.reviewReason ?? null,
    label: definition?.label ?? null,
  };
}

/**
 * Parse the Audit Report's persisted `policy_rule_results` blob into
 * render rows, ordered R1…R9 (Section 9.4 table order) followed by any
 * unknown ids in blob order. `null` (pre-engine report), a non-list or
 * only-malformed rows all degrade to an empty list — the caller decides
 * the fallback copy; an empty table is never rendered as "all pass".
 */
export function parseRuleResults(policyRuleResults: unknown): RuleTableRow[] {
  if (!Array.isArray(policyRuleResults)) return [];

  const byId = new Map<string, RuleTableRow>();
  const unknown: RuleTableRow[] = [];
  for (const entry of policyRuleResults) {
    const row = normalizeRow(entry);
    if (row === null) continue;
    if (RULE_BY_ID.has(row.rule)) {
      if (!byId.has(row.rule)) byId.set(row.rule, row); // first row wins
    } else {
      unknown.push(row);
    }
  }

  const ordered: RuleTableRow[] = [];
  for (const definition of POLICY_RULES) {
    const row = byId.get(definition.id);
    if (row !== undefined) ordered.push(row);
  }
  ordered.push(...unknown);
  return ordered;
}
