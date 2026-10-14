import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import 'diff_view.dart';
import 'review_providers.dart';
import 'review_reasons.dart';
import 'rule_results_view.dart';

/// Opens the approve-and-merge confirmation (MT-5.8-04): Section 14.2
/// mandates exactly what it shows — **task id, branch and diff stats**
/// — plus the rule-results summary from MT-5.8-02 as supporting
/// context, and the decision is bound to the resolution the sheet had
/// pinned when the dialog opened.
Future<void> showApproveConfirmDialog(
  BuildContext context, {
  required String taskId,
}) {
  return showDialog<void>(
    context: context,
    builder: (BuildContext context) => ApproveConfirmDialog(taskId: taskId),
  );
}

class ApproveConfirmDialog extends ConsumerStatefulWidget {
  const ApproveConfirmDialog({super.key, required this.taskId});

  final String taskId;

  @override
  ConsumerState<ApproveConfirmDialog> createState() =>
      _ApproveConfirmDialogState();
}

class _ApproveConfirmDialogState extends ConsumerState<ApproveConfirmDialog> {
  bool _submitting = false;

  /// What the dialog opened on — captured **once** so a background
  /// refresh can never silently rebind the confirmation to a newer
  /// resolution (MT-5.8-04 risk note's strict reading).
  Resolution? _resolution;
  Task? _task;
  AuditReport? _report;

  @override
  void initState() {
    super.initState();
    final ReviewState state = ref.read(reviewProvider(widget.taskId));
    _resolution = state.pinnedResolution;
    _task = state.task;
    _report = state.report;
  }

  @override
  Widget build(BuildContext context) {
    final ReviewState state = ref.watch(reviewProvider(widget.taskId));
    final Resolution? resolution = _resolution;
    final Task? task = _task;
    if (resolution == null || task == null) {
      // Nothing to approve — the sheet never fakes a confirmation.
      return AlertDialog(
        title: const Text('Approve and merge'),
        content: const Text('There is no submission to approve.'),
        actions: <Widget>[
          TextButton(
            key: const ValueKey<String>('review-approve-close'),
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      );
    }

    final AuditReport? report = _report;
    final (int failed, int passed) = _ruleCounts(report);

    return AlertDialog(
      title: const Text('Approve and merge?'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _factRow(
              context,
              key: const ValueKey<String>('review-approve-task'),
              label: 'Task',
              value: task.id,
            ),
            _factRow(
              context,
              key: const ValueKey<String>('review-approve-branch'),
              label: 'Branch',
              value: resolution.branchName,
            ),
            _factRow(
              context,
              key: const ValueKey<String>('review-approve-diff-stats'),
              label: 'Diff',
              value: diffStatsLabel(resolution),
            ),
            const SizedBox(height: 8),
            if (report == null)
              Text(
                key: const ValueKey<String>('review-approve-rules-summary'),
                'No audit report for this submission — approving on the '
                'execution summary and diff alone.',
                style: Theme.of(context).textTheme.bodySmall,
              )
            else
              Text(
                key: const ValueKey<String>('review-approve-rules-summary'),
                failed == 0
                    ? 'All $passed rules passed.'
                    : '$failed of ${failed + passed} rules failed:',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            if (report != null && failed > 0)
              for (final RuleResultRow row in _failingRules(report))
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    '${row.rule} · ${policyRuleLabel(row.rule)}'
                    '${row.reviewReason == null ? '' : ' — ${row.reviewReason}'}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.error,
                        ),
                  ),
                ),
          ],
        ),
      ),
      actions: <Widget>[
        TextButton(
          key: const ValueKey<String>('review-approve-cancel'),
          onPressed: _submitting ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          key: const ValueKey<String>('review-approve-confirm'),
          onPressed: (_submitting || !state.actionsEnabled)
              ? null
              : () => _submit(resolution.id, task.version),
          child: _submitting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Approve and merge'),
        ),
      ],
    );
  }

  Future<void> _submit(String resolutionId, int version) async {
    final ReviewState current = ref.read(reviewProvider(widget.taskId));
    if (current.pinnedResolution?.id != resolutionId) {
      // Background refresh re-pinned the sheet while the confirmation
      // was open — invalidate it (MT-5.8-04 risk note's strict
      // reading) instead of sending against a resolution the user has
      // not seen.
      ref.read(reviewProvider(widget.taskId).notifier).noteStaleConfirmation();
      if (mounted) {
        Navigator.of(context).pop();
      }
      return;
    }
    setState(() => _submitting = true);
    await ref
        .read(reviewProvider(widget.taskId).notifier)
        .approve(resolutionId: resolutionId, version: version);
    if (mounted) {
      Navigator.of(context).pop();
    }
  }

  static Widget _factRow(
    BuildContext context, {
    required Key key,
    required String label,
    required String value,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 64,
            child: Text(
              label,
              style: Theme.of(context)
                  .textTheme
                  .labelMedium
                  ?.copyWith(color: Theme.of(context).colorScheme.outline),
            ),
          ),
          Expanded(
            child: Text(
              key: key,
              value,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }
}

(int failed, int passed) _ruleCounts(AuditReport? report) {
  if (report == null) {
    return (0, 0);
  }
  final List<RuleResultRow>? rows = parseRuleResults(report.policyRuleResults);
  if (rows == null) {
    return (0, 0);
  }
  final int failed = rows.where((RuleResultRow r) => !r.passed).length;
  return (failed, rows.length - failed);
}

List<RuleResultRow> _failingRules(AuditReport report) {
  final List<RuleResultRow>? rows = parseRuleResults(report.policyRuleResults);
  if (rows == null) {
    return const <RuleResultRow>[];
  }
  return rows.where((RuleResultRow r) => !r.passed).toList();
}
