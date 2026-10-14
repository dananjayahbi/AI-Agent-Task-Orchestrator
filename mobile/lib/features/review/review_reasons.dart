/// Canonical Section 8.4 review reasons with friendly labels (MT-5.8-01).
///
/// ADR-010 / Section 20.5 discipline: the canonical wire strings are
/// never renamed or re-spelled here — this table only pairs each one
/// with human copy. Unknown values (a server-side catalog addition the
/// app has not seen) fall back to the canonical string itself, so the
/// sheet renders exactly what the backend sent and never invents a
/// reason.
library;

/// The twelve Section 8.4 members, in plan order.
const List<String> kCanonicalReviewReasons = <String>[
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
];

const Map<String, String> _reviewReasonLabels = <String, String>{
  'self_flagged': 'Coder asked for review',
  'scope_violation': 'Changes outside the task scope',
  'test_failure': 'Tests failed or produced no evidence',
  'migration_detected': 'Database migration detected',
  'sensitive_config_changed': 'Sensitive configuration changed',
  'critical_path_changed': 'Critical path changed',
  'diff_over_threshold': 'Diff over the size threshold',
  'low_confidence': 'Auditor confidence too low',
  'retry_exhausted': 'Retries exhausted',
  'merge_conflict': 'Merge conflict',
  'auditor_flagged': 'Auditor flagged the submission',
  'policy_forced_review': 'Policy forces review (auto-complete off)',
};

/// Friendly label for [reason]; the canonical string is always rendered
/// alongside it by the callers (Section 20.5 — canonical values kept).
String friendlyReviewReason(String reason) =>
    _reviewReasonLabels[reason] ?? reason;

/// True when [reason] is a Section 8.4 member this build knows.
bool isKnownReviewReason(String reason) =>
    _reviewReasonLabels.containsKey(reason);

/// Section 9.4 rule ids in table order with their display names — the
/// engine persists all nine every time (Section 9.4 design note), so
/// the sheet renders every row, never a subset.
const List<(String, String)> kPolicyRuleLabels = <(String, String)>[
  ('R1', 'Tests'),
  ('R2', 'Scope'),
  ('R3', 'Critical paths'),
  ('R4', 'Migrations'),
  ('R5', 'Sensitive config'),
  ('R6', 'Diff size'),
  ('R7', 'Confidence'),
  ('R8', 'Auditor flag'),
  ('R9', 'Switch'),
];

/// Display name for a Section 9.4 rule id; unknown ids (a future rule
/// outside this build's table) render verbatim — never dropped.
String policyRuleLabel(String ruleId) {
  for (final (String id, String label) in kPolicyRuleLabels) {
    if (id == ruleId) {
      return label;
    }
  }
  return ruleId;
}
