/**
 * Review-reason presentation (MT-4.8-01 / MT-4.4-03; Section 8.4 canonical
 * enum, Section 20.5 "reason values verbatim — nothing invented").
 *
 * The canonical snake_case code is always surfaced (verbatim from
 * Section 8.4); the friendly label is presentation only — the code is the
 * contract, the label never replaces it. Unknown/future codes degrade to
 * the raw code rather than an invented explanation.
 */

/** Section 8.4 — the closed canonical enum, in plan order. */
export const REVIEW_REASONS = [
  'self_flagged',
  'scope_violation',
  'test_failure',
  'migration_detected',
  'sensitive_config_changed',
  'critical_path_changed',
  'diff_over_threshold',
  'low_confidence',
  'retry_exhausted',
  'merge_conflict',
  'auditor_flagged',
  'policy_forced_review',
] as const;

export type ReviewReason = (typeof REVIEW_REASONS)[number];

const REASON_LABELS: Record<ReviewReason, string> = {
  self_flagged: 'Coder flagged their own work',
  scope_violation: 'Changes outside the target scope',
  test_failure: 'Tests failed or missing',
  migration_detected: 'Database migration detected',
  sensitive_config_changed: 'Sensitive config changed',
  critical_path_changed: 'Critical path touched',
  diff_over_threshold: 'Diff over the size threshold',
  low_confidence: 'Audit confidence too low',
  retry_exhausted: 'Automatic retries exhausted',
  merge_conflict: 'Merge conflict',
  auditor_flagged: 'Auditor flagged a risk',
  policy_forced_review: 'Policy requires a human review',
};

export function isReviewReason(value: unknown): value is ReviewReason {
  return typeof value === 'string' && (REVIEW_REASONS as readonly string[]).includes(value);
}

/** Friendly label for a Section 8.4 member; unknown codes render as-is. */
export function reviewReasonLabel(reason: string | null): string {
  if (reason === null || reason === '') {
    return 'No reason recorded';
  }
  return isReviewReason(reason) ? REASON_LABELS[reason] : reason;
}
