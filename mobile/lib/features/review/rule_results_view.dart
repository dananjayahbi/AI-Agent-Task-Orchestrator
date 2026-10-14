import 'dart:convert';

import 'package:built_value/json_object.dart';
import 'package:flutter/material.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import 'review_reasons.dart';

/// One parsed `policy_rule_results` row — the Section 9.4 shape the
/// engine persists: `{rule, passed, review_reason}` (stable keys,
/// WP-3.4). Never computed client-side: the backend is the authority
/// (Sections 9.4, 20.5).
class RuleResultRow {
  const RuleResultRow({
    required this.rule,
    required this.passed,
    this.reviewReason,
  });

  final String rule;
  final bool passed;
  final String? reviewReason;
}

/// Parse the report's `policy_rule_results` JSON blob defensively:
/// rows missing the stable keys are dropped (never guessed), and a
/// non-list / empty value reads as null → the honest "not recorded"
/// state (Sections 20.3, 20.5).
List<RuleResultRow>? parseRuleResults(JsonObject? blob) {
  final Object? value = blob?.value;
  if (value is! List<Object?> || value.isEmpty) {
    return null;
  }
  final List<RuleResultRow> rows = <RuleResultRow>[];
  for (final Object? item in value) {
    if (item is! Map<Object?, Object?>) {
      continue;
    }
    final Object? rule = item['rule'];
    final Object? passed = item['passed'];
    if (rule is! String || passed is! bool) {
      continue;
    }
    final Object? reason = item['review_reason'];
    rows.add(RuleResultRow(
      rule: rule,
      passed: passed,
      reviewReason: reason is String ? reason : null,
    ));
  }
  return rows.isEmpty ? null : rows;
}

/// The rule-results region of the review sheet (MT-5.8-02): every
/// Section 9.4 rule outcome with the failing rule's review reason and
/// the persisted engine version — all read verbatim from the backend.
///
/// Layout follows the MT's ergonomics note: failing rules render first
/// as full rows (every failing rule visible without truncation), the
/// passing block collapses behind one disclosure when failures exist;
/// a fully-passing report renders all nine rows (Section 9.4 persists
/// every rule — showing only failures would hide the "exactly why"
/// context).
class RuleResultsView extends StatelessWidget {
  const RuleResultsView({super.key, required this.report});

  final AuditReport report;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final List<RuleResultRow>? rows =
        parseRuleResults(report.policyRuleResults);
    if (rows == null) {
      // Pre-audit escalation or pre-engine report — reason + summary
      // only, never a fabricated pass table (Section 8.5; 20.3).
      return ReviewSectionCard(
        title: 'Rule results',
        child: Text(
          key: const ValueKey<String>('review-rules-missing'),
          'No policy rule results recorded for this report.',
          style: theme.textTheme.bodyMedium
              ?.copyWith(color: theme.colorScheme.outline),
        ),
      );
    }

    final List<RuleResultRow> ordered = List<RuleResultRow>.of(rows)
      ..sort(_failuresFirst);
    final List<RuleResultRow> failing =
        ordered.where((RuleResultRow r) => !r.passed).toList();
    final List<RuleResultRow> passing =
        ordered.where((RuleResultRow r) => r.passed).toList();

    return ReviewSectionCard(
      title: 'Rule results',
      trailing: Text(
        key: const ValueKey<String>('review-rules-engine-version'),
        report.policyEngineVersion == null
            ? 'engine version not recorded'
            : 'engine ${report.policyEngineVersion}',
        style: theme.textTheme.labelSmall
            ?.copyWith(color: theme.colorScheme.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          if (failing.isEmpty)
            for (final RuleResultRow row in ordered) _RuleRow(row: row)
          else ...<Widget>[
            for (final RuleResultRow row in failing) _RuleRow(row: row),
            const SizedBox(height: 8),
            _PassingDisclosure(passing: passing),
          ],
        ],
      ),
    );
  }

  /// Failures first, then Section 9.4 table order (stable within each
  /// group — `sort` must not reorder equals unpredictably).
  static int _failuresFirst(RuleResultRow a, RuleResultRow b) {
    if (a.passed != b.passed) {
      return a.passed ? 1 : -1;
    }
    const List<String> order = <String>[
      'R1',
      'R2',
      'R3',
      'R4',
      'R5',
      'R6',
      'R7',
      'R8',
      'R9',
    ];
    final int ai = order.indexOf(a.rule);
    final int bi = order.indexOf(b.rule);
    return (ai == -1 ? 99 : ai).compareTo(bi == -1 ? 99 : bi);
  }
}

class _RuleRow extends StatelessWidget {
  const _RuleRow({required this.row});

  final RuleResultRow row;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final bool failed = !row.passed;
    final String? reason = row.reviewReason;
    return Container(
      key: ValueKey<String>('review-rule-${row.rule}'),
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: failed
            ? theme.colorScheme.errorContainer.withValues(alpha: 0.45)
            : theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(
            failed ? Icons.close_rounded : Icons.check_rounded,
            size: 18,
            key: ValueKey<String>('review-rule-status-${row.rule}'),
            color: failed ? theme.colorScheme.error : theme.colorScheme.primary,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  '${row.rule} · ${policyRuleLabel(row.rule)}',
                  style: theme.textTheme.bodyMedium,
                ),
                if (failed && reason != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      'Review reason: $reason — ${friendlyReviewReason(reason)}',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.error,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PassingDisclosure extends StatelessWidget {
  const _PassingDisclosure({required this.passing});

  final List<RuleResultRow> passing;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: ExpansionTile(
        key: const ValueKey<String>('review-rules-passing'),
        title: Text(
          '${passing.length} passing '
          '${passing.length == 1 ? 'rule' : 'rules'} (collapsed)',
          style: theme.textTheme.bodyMedium,
        ),
        childrenPadding: const EdgeInsets.fromLTRB(10, 0, 10, 8),
        children: <Widget>[
          for (final RuleResultRow row in passing) _RuleRow(row: row),
        ],
      ),
    );
  }
}

/// The Section 10.5 evidence display (MT-5.8-02): commands with exit
/// codes, `lint_clean`, acceptance-criteria results, confidence,
/// proposed verdict and the resulting policy decision — plus unknown
/// keys collapsed rather than guessed (Section 20.5).
class EvidenceView extends StatelessWidget {
  const EvidenceView({super.key, required this.report});

  final AuditReport report;

  /// Evidence keys this widget renders explicitly; every other key
  /// lands in the collapsed "additional keys" disclosure.
  static const Set<String> knownKeys = <String>{
    'commands',
    'lint_clean',
    'acceptance_criteria_results',
  };

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Map<String, Object?> evidence = _evidenceMap(report);
    final Object? commands = evidence['commands'];
    final Object? lintClean = evidence['lint_clean'];
    final Object? criteria = evidence['acceptance_criteria_results'];
    final List<String> unknownKeys = evidence.keys
        .where((String key) => !knownKeys.contains(key))
        .toList()
      ..sort();

    return ReviewSectionCard(
      title: 'Evidence',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: <Widget>[
              _MetaChip(
                key: const ValueKey<String>('review-evidence-confidence'),
                label: 'Confidence ${report.confidence} of 5',
              ),
              _MetaChip(
                key: const ValueKey<String>('review-evidence-verdict'),
                label: 'Proposed verdict: ${report.proposedVerdict.name}',
              ),
              _MetaChip(
                key: const ValueKey<String>('review-evidence-decision'),
                label: report.policyDecision == null
                    ? 'Policy decision: not yet evaluated'
                    : 'Policy decision: ${report.policyDecision!.name}',
              ),
              if (lintClean is bool)
                _MetaChip(
                  key: const ValueKey<String>('review-evidence-lint'),
                  label: lintClean ? 'Lint clean' : 'Lint not clean',
                ),
            ],
          ),
          if (criteria is List<Object?> && criteria.isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            Text('Acceptance criteria', style: theme.textTheme.titleSmall),
            for (final Object? item in criteria)
              if (item is Map<Object?, Object?>)
                _CriterionRow(
                  criterion: '${item['criterion'] ?? ''}',
                  met: item['met'] == true,
                ),
          ],
          if (commands is List<Object?> && commands.isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            Text('Commands run', style: theme.textTheme.titleSmall),
            for (final Object? item in commands)
              if (item is Map<Object?, Object?>)
                _CommandRow(
                  label: '${item['label'] ?? 'command'}',
                  command: '${item['command'] ?? ''}',
                  exitCode: item['exit_code'] is int
                      ? item['exit_code']! as int
                      : null,
                  summary: item['summary'] is String
                      ? item['summary']! as String
                      : null,
                ),
          ],
          if (unknownKeys.isNotEmpty) ...<Widget>[
            const SizedBox(height: 4),
            _UnknownEvidenceKeys(
              keys: unknownKeys,
              evidence: evidence,
            ),
          ],
        ],
      ),
    );
  }

  static Map<String, Object?> _evidenceMap(AuditReport report) {
    final Object? value = report.evidence?.value;
    if (value is Map<Object?, Object?>) {
      return <String, Object?>{
        for (final MapEntry<Object?, Object?> entry in value.entries)
          if (entry.key is String) entry.key! as String: entry.value,
      };
    }
    return <String, Object?>{};
  }
}

class _CriterionRow extends StatelessWidget {
  const _CriterionRow({required this.criterion, required this.met});

  final String criterion;
  final bool met;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(
            met ? Icons.check_rounded : Icons.close_rounded,
            size: 16,
            color: met ? theme.colorScheme.primary : theme.colorScheme.error,
          ),
          const SizedBox(width: 6),
          Expanded(child: Text(criterion, style: theme.textTheme.bodySmall)),
        ],
      ),
    );
  }
}

class _CommandRow extends StatelessWidget {
  const _CommandRow({
    required this.label,
    required this.command,
    required this.exitCode,
    required this.summary,
  });

  final String label;
  final String command;
  final int? exitCode;
  final String? summary;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final int? code = exitCode;
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(label, style: theme.textTheme.labelMedium),
              ),
              if (code != null)
                Container(
                  key: ValueKey<String>('review-command-exit-$label'),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: (code == 0
                        ? theme.colorScheme.primaryContainer
                        : theme.colorScheme.errorContainer),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    'exit $code',
                    style: theme.textTheme.labelSmall,
                  ),
                ),
            ],
          ),
          if (command.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal, // own scroll, no page scroll
                child: Text(
                  command,
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ),
          if (summary != null && summary!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(summary!, style: theme.textTheme.bodySmall),
            ),
        ],
      ),
    );
  }
}

/// Unknown evidence keys render collapsed — key names plus a compact
/// JSON preview; nothing is guessed, nothing invented (Section 20.5).
class _UnknownEvidenceKeys extends StatelessWidget {
  const _UnknownEvidenceKeys({required this.keys, required this.evidence});

  final List<String> keys;
  final Map<String, Object?> evidence;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: ExpansionTile(
        key: const ValueKey<String>('review-evidence-unknown-keys'),
        title: Text(
          'Additional evidence keys (${keys.length})',
          style: theme.textTheme.bodyMedium,
        ),
        childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
        children: <Widget>[
          for (final String key in keys)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                '$key: ${_preview(evidence[key])}',
                style: theme.textTheme.bodySmall
                    ?.copyWith(fontFamily: 'monospace'),
              ),
            ),
        ],
      ),
    );
  }

  static const int _previewLimit = 400;

  static String _preview(Object? value) {
    final String encoded = jsonEncode(value);
    if (encoded.length <= _previewLimit) {
      return encoded;
    }
    return '${encoded.substring(0, _previewLimit)}…';
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label, super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(label, style: theme.textTheme.labelMedium),
    );
  }
}

/// Shared section card for the sheet's regions (one visual language;
/// Section 14.1 order maintained by the screen that stacks them).
class ReviewSectionCard extends StatelessWidget {
  const ReviewSectionCard({
    super.key,
    required this.title,
    required this.child,
    this.trailing,
  });

  final String title;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(title, style: theme.textTheme.titleMedium),
              ),
              if (trailing != null) trailing!,
            ],
          ),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }
}
