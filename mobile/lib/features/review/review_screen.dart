import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/read_error_messages.dart';
import 'approve_dialog.dart';
import 'diff_view.dart';
import 'reassign_dialog.dart';
import 'request_changes_dialog.dart';
import 'review_providers.dart';
import 'review_reasons.dart';
import 'rule_results_view.dart';

/// Review sheet area (parent plan Section 14.1): reason and rule
/// results, execution summary, auditor notes, diff, and the three
/// actions in a fixed bar — WP-5.8 (MT-5.8-01 layout; regions owned by
/// MT-5.8-02 rule results/evidence and MT-5.8-03 diff).
///
/// * **Addressability:** constructed with the task id (board push or a
///   future WP-5.9 deep link — the route contract is id-based); no id
///   renders an honest empty state, never a fabricated sheet.
/// * **Sheet-vs-screen (recorded decision):** a full-height pushed
///   screen, not a bottom sheet — it is a named route area, must
///   survive deep links by id (WP-5.9 contract) and carries an action
///   bar on small screens. Gesture dismissal is the system back; the
///   only draft state lives in the dialogs, whose discard safety is
///   MT-5.8-05's.
/// * **Session constraints:** the app-level biometric gate wraps the
///   whole navigator (Section 14.2 — gate is app-level, not per-sheet);
///   offline shows the clear Section 14.2 state with every mutation
///   disabled and nothing queued.
class ReviewScreen extends ConsumerWidget {
  const ReviewScreen({super.key, this.taskId});

  /// The task to review; null when the route carried no id.
  final String? taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Review sheet')),
      body: taskId == null
          ? const _NoTaskSelected()
          : _ReviewBody(taskId: taskId!),
      bottomNavigationBar:
          taskId == null ? null : _ReviewActionsBar(taskId: taskId!),
    );
  }
}

class _NoTaskSelected extends StatelessWidget {
  const _NoTaskSelected();

  @override
  Widget build(BuildContext context) {
    return Center(
      key: const ValueKey<String>('review-no-task'),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(
          'No task selected — open one from the board.',
          textAlign: TextAlign.center,
          style: Theme.of(context)
              .textTheme
              .bodyMedium
              ?.copyWith(color: Theme.of(context).colorScheme.outline),
        ),
      ),
    );
  }
}

class _ReviewBody extends ConsumerWidget {
  const _ReviewBody({required this.taskId});

  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ReviewState state = ref.watch(reviewProvider(taskId));
    switch (state.status) {
      case ReviewStatus.loading:
        return const Center(
          key: ValueKey<String>('review-loading'),
          child: CircularProgressIndicator(),
        );
      case ReviewStatus.error:
        return Center(
          key: const ValueKey<String>('review-error'),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Text(
                  friendlyReadErrorMessage(state.error!),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  key: const ValueKey<String>('review-retry'),
                  onPressed: () =>
                      ref.read(reviewProvider(taskId).notifier).load(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Try again'),
                ),
              ],
            ),
          ),
        );
      case ReviewStatus.offline:
        return Center(
          key: const ValueKey<String>('review-offline'),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Icon(
                  Icons.cloud_off,
                  size: 40,
                  color: Theme.of(context).colorScheme.outline,
                ),
                const SizedBox(height: 12),
                Text(
                  key: const ValueKey<String>('review-offline-copy'),
                  'You are offline — review actions are disabled and '
                  'nothing can be queued (decisions must be current).',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  key: const ValueKey<String>('review-offline-retry'),
                  onPressed: () =>
                      ref.read(reviewProvider(taskId).notifier).load(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Try again'),
                ),
              ],
            ),
          ),
        );
      case ReviewStatus.ready:
        return _ready(context, ref, state);
    }
  }

  Widget _ready(BuildContext context, WidgetRef ref, ReviewState state) {
    final Task task = state.task!;
    final Resolution? resolution = state.pinnedResolution;
    final AuditReport? report = state.report;
    final ThemeData theme = Theme.of(context);
    return RefreshIndicator(
      onRefresh: () => ref.read(reviewProvider(taskId).notifier).load(),
      child: ListView(
        key: const ValueKey<String>('review-scroll'),
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 24),
        children: <Widget>[
          if (state.notice != null)
            _NoticeBanner(
              message: state.notice!,
              onDismiss: () =>
                  ref.read(reviewProvider(taskId).notifier).dismissNotice(),
            ),
          if (state.outcome != null) _OutcomeBanner(outcome: state.outcome!),
          _ReasonCard(task: task),
          if (report == null)
            ReviewSectionCard(
              title: 'Rule results',
              child: Text(
                key: const ValueKey<String>('review-report-missing'),
                'No audit report for this submission — showing the reason '
                'and execution summary only.',
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.outline),
              ),
            )
          else
            RuleResultsView(report: report),
          _ExecutionSummaryCard(resolution: resolution),
          _AuditorNotesCard(report: report),
          if (report != null) EvidenceView(report: report),
          if (resolution != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: DiffRegionView(resolution: resolution),
            ),
        ],
      ),
    );
  }
}

/// Section 14.1's first region: escalation reason(s) — canonical
/// Section 8.4 string retained with a friendly label (ADR-010).
class _ReasonCard extends StatelessWidget {
  const _ReasonCard({required this.task});

  final Task task;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final String? reason = task.reviewReason;
    return ReviewSectionCard(
      title: 'Escalation reason',
      child: reason == null || reason.isEmpty
          ? Text(
              key: const ValueKey<String>('review-reason-empty'),
              'No escalation reason recorded.',
              style: theme.textTheme.bodyMedium
                  ?.copyWith(color: theme.colorScheme.outline),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  key: const ValueKey<String>('review-reason-friendly'),
                  friendlyReviewReason(reason),
                  style: theme.textTheme.bodyLarge,
                ),
                const SizedBox(height: 4),
                Text(
                  key: const ValueKey<String>('review-reason-canonical'),
                  reason,
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontFamily: 'monospace',
                    color: theme.colorScheme.outline,
                  ),
                ),
              ],
            ),
    );
  }
}

class _ExecutionSummaryCard extends StatelessWidget {
  const _ExecutionSummaryCard({required this.resolution});

  final Resolution? resolution;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Resolution? row = resolution;
    return ReviewSectionCard(
      title: 'Execution summary',
      child: row == null
          ? Text(
              key: const ValueKey<String>('review-summary-empty'),
              'No submission yet — nothing to review.',
              style: theme.textTheme.bodyMedium
                  ?.copyWith(color: theme.colorScheme.outline),
            )
          : Text(
              key: const ValueKey<String>('review-execution-summary'),
              row.executionSummary.trim().isEmpty
                  ? 'No execution summary provided.'
                  : row.executionSummary,
              style: theme.textTheme.bodyMedium,
            ),
    );
  }
}

class _AuditorNotesCard extends StatelessWidget {
  const _AuditorNotesCard({required this.report});

  final AuditReport? report;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final AuditReport? row = report;
    return ReviewSectionCard(
      title: 'Auditor notes',
      child: row == null || row.auditorNotes.trim().isEmpty
          ? Text(
              key: const ValueKey<String>('review-auditor-notes-empty'),
              row == null
                  ? 'No auditor notes — no audit report for this submission.'
                  : 'No auditor notes.',
              style: theme.textTheme.bodyMedium
                  ?.copyWith(color: theme.colorScheme.outline),
            )
          : Text(
              key: const ValueKey<String>('review-auditor-notes'),
              row.auditorNotes,
              style: theme.textTheme.bodyMedium,
            ),
    );
  }
}

/// The Section 14.2 notice strip (stale rejection, conflicts,
/// transport failures) — informational, dismissible.
class _NoticeBanner extends StatelessWidget {
  const _NoticeBanner({required this.message, required this.onDismiss});

  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      key: const ValueKey<String>('review-notice'),
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: <Widget>[
          const Icon(Icons.info_outline, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              key: const ValueKey<String>('review-notice-text'),
              message,
              style: theme.textTheme.bodySmall,
            ),
          ),
          IconButton(
            key: const ValueKey<String>('review-notice-dismiss'),
            icon: const Icon(Icons.close, size: 18),
            onPressed: onDismiss,
          ),
        ],
      ),
    );
  }
}

/// Post-decision outcome (Section 8.1 sub-status): approve shows
/// merge-pending — never a premature "completed" (ADR-008).
class _OutcomeBanner extends StatelessWidget {
  const _OutcomeBanner({required this.outcome});

  final ReviewOutcome outcome;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final bool pending = outcome.mergePending;
    return Container(
      key: ValueKey<String>(
          'review-outcome-${decisionWireName(outcome.decision)}${pending ? '-pending' : ''}'),
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: pending
            ? theme.colorScheme.tertiaryContainer
            : theme.colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: <Widget>[
          Icon(
            pending ? Icons.hourglass_top : Icons.check_circle_outline,
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              pending
                  ? 'Approved — merge pending (merge status: '
                      '${outcome.task.mergeStatus}).'
                  : '${decisionWireName(outcome.decision)} recorded — task '
                      'is now ${outcome.task.state}.',
              style: theme.textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

/// The fixed action bar (Section 14.1's three actions): reachable on
/// small screens above the safe area, disabled while offline or a
/// submission is in flight (Section 14.2 — no queued mutations).
class _ReviewActionsBar extends ConsumerWidget {
  const _ReviewActionsBar({required this.taskId});

  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ReviewState state = ref.watch(reviewProvider(taskId));
    final bool enabled = state.actionsEnabled;
    final bool canApprove = enabled && state.pinnedResolution != null;
    return SafeArea(
      child: Container(
        key: const ValueKey<String>('review-actions-bar'),
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          border: Border(
            top: BorderSide(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
        ),
        child: Row(
          children: <Widget>[
            Expanded(
              child: FilledButton(
                key: const ValueKey<String>('review-action-approve'),
                onPressed: canApprove
                    ? () => showApproveConfirmDialog(context, taskId: taskId)
                    : null,
                child: const Text('Approve'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton(
                key: const ValueKey<String>('review-action-request-changes'),
                onPressed: enabled
                    ? () => showRequestChangesDialog(context, taskId: taskId)
                    : null,
                child: const Text('Request changes'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton(
                key: const ValueKey<String>('review-action-reassign'),
                onPressed: enabled
                    ? () => showReassignDialog(context, taskId: taskId)
                    : null,
                child: const Text('Reassign'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
