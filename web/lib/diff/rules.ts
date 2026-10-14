'use client';

/**
 * Policy-rule vocabulary shared by the diff viewer's flag markers
 * (MT-4.7-05; Section 9.4's rule table; Section 20.5 traceability).
 *
 * Only the ids the marker layer needs live here: the Section 9.4
 * **file-based** rules whose fail conditions are expressed as changed
 * files matching globs. The full R1–R9 table rendering belongs to the
 * review panel (WP-4.8) and reads the persisted rows directly.
 */

/** The Section 9.4 file-based rule ids (fail conditions over changed files). */
export const FILE_BASED_RULES = ['R2', 'R3', 'R4', 'R5'] as const;

export type RuleId = (typeof FILE_BASED_RULES)[number];

/** Human labels for the file-based rules (marker tooltips; text always shown too). */
export const RULE_LABELS: Record<RuleId, string> = {
  R2: 'Scope',
  R3: 'Critical paths',
  R4: 'Migrations',
  R5: 'Sensitive config',
};
