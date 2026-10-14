import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/read_error_messages.dart';
import 'attachment_list_section.dart';
import 'checkpoint_feed_view.dart';
import 'inert_markdown.dart';
import 'task_detail_providers.dart';

/// Task detail area (parent plan Section 14.1): summary, criteria,
/// checkpoint stream, resolutions, attachments — WP-5.7 (MT-5.7-01).
///
/// * **Addressability:** constructed with the task id (board push or
///   deep link — WP-5.9 owns full routing); an absent id renders an
///   honest empty state, never a fabricated task (Section 20.3).
/// * **Data:** one generated-client load through
///   [taskDetailProvider] (Section 14.3 / NFR-11) with loading, error
///   and offline-stale states (Section 20.3/14.2); errors map from
///   catalog codes only (Section 20.4 item 5).
/// * **Regions owned elsewhere in the WP:** the checkpoint stream
///   (MT-5.7-02 [CheckpointFeedView]) and the attachment list/viewer
///   (MT-5.7-03 [AttachmentListSection]).
/// * **Read-only:** no mutating action exists on this screen — it is
///   safe in the offline-stale state by construction (Section 14.2).
class TaskDetailScreen extends ConsumerWidget {
  const TaskDetailScreen({super.key, this.taskId});

  /// The task to display; null when the route carried no id.
  final String? taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Task detail')),
      body: taskId == null
          ? const _NoTaskSelected()
          : _TaskDetailBody(taskId: taskId!),
    );
  }
}

class _NoTaskSelected extends StatelessWidget {
  const _NoTaskSelected();

  @override
  Widget build(BuildContext context) {
    return Center(
      key: const ValueKey<String>('task-detail-no-task'),
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

class _TaskDetailBody extends ConsumerWidget {
  const _TaskDetailBody({required this.taskId});

  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final TaskDetailState state = ref.watch(taskDetailProvider(taskId));
    switch (state.status) {
      case TaskDetailStatus.loading:
        return const Center(
          key: ValueKey<String>('task-detail-loading'),
          child: CircularProgressIndicator(),
        );
      case TaskDetailStatus.error:
        return Center(
          key: const ValueKey<String>('task-detail-error'),
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
                  key: const ValueKey<String>('task-detail-retry'),
                  onPressed: () =>
                      ref.read(taskDetailProvider(taskId).notifier).load(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Try again'),
                ),
              ],
            ),
          ),
        );
      case TaskDetailStatus.ready:
        return _ready(context, ref, state);
    }
  }

  Widget _ready(BuildContext context, WidgetRef ref, TaskDetailState state) {
    final Task task = state.task!;
    final ThemeData theme = Theme.of(context);
    return RefreshIndicator(
      onRefresh: () => ref.read(taskDetailProvider(taskId).notifier).load(),
      child: ListView(
        key: const ValueKey<String>('task-detail-scroll'),
        padding: const EdgeInsets.only(bottom: 24),
        children: <Widget>[
          if (state.isStale)
            Container(
              key: const ValueKey<String>('task-detail-stale-banner'),
              margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.secondaryContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: <Widget>[
                  Icon(
                    Icons.cloud_off,
                    size: 20,
                    color: theme.colorScheme.onSecondaryContainer,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      state.error == null
                          ? 'Offline — showing the last loaded details.'
                          : '${friendlyReadErrorMessage(state.error!)} '
                              'Showing the last loaded details.',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSecondaryContainer,
                      ),
                    ),
                  ),
                ],
              ),
            ),

          // --- Summary (Section 14.1) -----------------------------------
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  task.title,
                  key: const ValueKey<String>('task-detail-title'),
                  style: theme.textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: <Widget>[
                    Chip(
                      key: const ValueKey<String>('task-detail-state'),
                      label: Text(task.state.name),
                      visualDensity: VisualDensity.compact,
                    ),
                    Chip(
                      key: const ValueKey<String>('task-detail-priority'),
                      label: Text('P: ${task.priority.name}'),
                      visualDensity: VisualDensity.compact,
                    ),
                    if (task.workerAgentId != null)
                      Chip(
                        key: const ValueKey<String>('task-detail-worker'),
                        label: Text('Worker: ${task.workerAgentId}'),
                        visualDensity: VisualDensity.compact,
                      ),
                  ],
                ),
                if (task.latestFeedback.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 8),
                  Text('Latest feedback', style: theme.textTheme.titleSmall),
                  InertMarkdown(data: task.latestFeedback),
                ],
                const SizedBox(height: 8),
                Text('Description', style: theme.textTheme.titleSmall),
                const SizedBox(height: 4),
                // Inert rendering, Principle P10: markdown is data.
                InertMarkdown(
                  key: const ValueKey<String>('task-detail-description'),
                  data: task.description,
                ),
              ],
            ),
          ),

          // --- Acceptance criteria (Section 14.1) -----------------------
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Acceptance criteria',
                  style: theme.textTheme.titleMedium,
                ),
                const SizedBox(height: 4),
                if (task.acceptanceCriteria.isEmpty)
                  Text(
                    'No acceptance criteria.',
                    key: const ValueKey<String>('task-detail-no-criteria'),
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.outline,
                    ),
                  )
                else
                  for (int i = 0; i < task.acceptanceCriteria.length; i++)
                    Padding(
                      key: ValueKey<String>('task-detail-criterion-$i'),
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('${i + 1}. '),
                          Expanded(
                            child: Text(task.acceptanceCriteria[i]),
                          ),
                        ],
                      ),
                    ),
              ],
            ),
          ),

          // --- Checkpoint stream region (live, MT-5.7-02) ---------------
          // Fixed-height region inside the scroll view: the feed owns
          // its own scrolling list, so long criteria above never starve
          // it and the feed stays bounded on mid-range devices
          // (RISK-13 analog).
          Padding(
            padding: const EdgeInsets.fromLTRB(0, 16, 0, 0),
            child: SizedBox(
              height: 360,
              child: CheckpointFeedView(taskId: taskId),
            ),
          ),

          // --- Resolutions (Section 14.1; summaries only) ---------------
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Resolutions', style: theme.textTheme.titleMedium),
                const SizedBox(height: 4),
                if (state.resolutions.isEmpty)
                  Text(
                    'No submissions yet.',
                    key: const ValueKey<String>('task-detail-no-resolutions'),
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.outline,
                    ),
                  )
                else
                  for (final Resolution resolution in state.resolutions)
                    Card(
                      key: ValueKey<String>(
                          'task-detail-resolution-${resolution.id}'),
                      margin: const EdgeInsets.symmetric(vertical: 4),
                      child: ListTile(
                        title: Text(
                          'Attempt ${resolution.attemptNumber} — '
                          '${resolution.branchName}',
                        ),
                        subtitle: Text(resolution.executionSummary),
                        trailing: resolution.requiresHumanAttention
                            ? const Icon(Icons.warning_amber_rounded)
                            : null,
                      ),
                    ),
              ],
            ),
          ),

          // --- Attachments entry points (MT-5.7-03) ---------------------
          AttachmentListSection(taskId: taskId),
        ],
      ),
    );
  }
}
