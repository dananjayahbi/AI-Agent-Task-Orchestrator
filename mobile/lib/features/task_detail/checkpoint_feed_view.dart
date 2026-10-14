import 'package:built_value/json_object.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/read_error_messages.dart';
import '../../core/realtime/realtime_providers.dart';
import '../../core/realtime/sse_client.dart';
import '../../core/realtime/sse_connection_status.dart';
import 'checkpoint_feed_providers.dart';

/// The checkpoint stream region of the Task detail screen (Section 14.1;
/// MT-5.7-02): reverse-chronological live rows with percent, message and
/// token usage (Section 13.2's feed spec applied to mobile).
///
/// Liveness is read from the shared [SseClient] the transport owns —
/// the polling fallback is labeled honestly, never as live
/// (Section 14.2, RISK-05).
class CheckpointFeedView extends ConsumerWidget {
  const CheckpointFeedView({super.key, required this.taskId});

  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final CheckpointFeedState state = ref.watch(checkpointFeedProvider(taskId));
    final SseClient client = ref.watch(sseClientProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  'Checkpoints',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              ValueListenableBuilder<SseConnectionStatus>(
                valueListenable: client.status,
                builder: (BuildContext context, SseConnectionStatus status, _) {
                  return Tooltip(
                    message: checkpointLivenessLabel(status),
                    child: Chip(
                      key: const ValueKey<String>('checkpoint-liveness'),
                      label: Text(checkpointLivenessLabel(status)),
                      visualDensity: VisualDensity.compact,
                    ),
                  );
                },
              ),
            ],
          ),
        ),
        if (state.isDegradedPolling)
          Padding(
            key: const ValueKey<String>('checkpoint-degraded-banner'),
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
            child: Text(
              'The live stream dropped — polling for new checkpoints.',
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: Theme.of(context).colorScheme.tertiary),
            ),
          ),
        Expanded(child: _body(context, ref, state)),
      ],
    );
  }

  Widget _body(
    BuildContext context,
    WidgetRef ref,
    CheckpointFeedState state,
  ) {
    switch (state.status) {
      case CheckpointFeedStatus.loading:
        return const Center(
          key: ValueKey<String>('checkpoint-feed-loading'),
          child: CircularProgressIndicator(),
        );
      case CheckpointFeedStatus.error:
        return Center(
          key: const ValueKey<String>('checkpoint-feed-error'),
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
                OutlinedButton.icon(
                  key: const ValueKey<String>('checkpoint-feed-retry'),
                  onPressed: () =>
                      ref.read(checkpointFeedProvider(taskId).notifier).load(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Try again'),
                ),
              ],
            ),
          ),
        );
      case CheckpointFeedStatus.ready:
        if (state.checkpoints.isEmpty) {
          return Center(
            key: const ValueKey<String>('checkpoint-feed-empty'),
            child: Text(
              'No checkpoints yet.',
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: Theme.of(context).colorScheme.outline),
            ),
          );
        }
        return RefreshIndicator(
          onRefresh: () =>
              ref.read(checkpointFeedProvider(taskId).notifier).load(),
          child: ListView.builder(
            key: const ValueKey<String>('checkpoint-feed-list'),
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: state.checkpoints.length + 1,
            itemBuilder: (BuildContext context, int index) {
              if (index == state.checkpoints.length) {
                return _footer(context, ref, state);
              }
              return _CheckpointRow(checkpoint: state.checkpoints[index]);
            },
          ),
        );
    }
  }

  Widget _footer(
      BuildContext context, WidgetRef ref, CheckpointFeedState state) {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        children: <Widget>[
          if (state.olderCursor != null)
            OutlinedButton(
              key: const ValueKey<String>('checkpoint-load-older'),
              onPressed: () =>
                  ref.read(checkpointFeedProvider(taskId).notifier).loadOlder(),
              child: const Text('Load older checkpoints'),
            ),
          // Padding so the last row clears the pull-to-refresh gap.
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}

/// Honest liveness copy for [status] — same vocabulary as the board
/// (MT-5.6-04); the polling fallback (Section 14.2) is never "Live".
String checkpointLivenessLabel(SseConnectionStatus status) {
  switch (status) {
    case SseConnectionStatus.disconnected:
      return 'Live updates off';
    case SseConnectionStatus.connecting:
      return 'Connecting…';
    case SseConnectionStatus.connected:
      return 'Live';
    case SseConnectionStatus.reconnecting:
      return 'Reconnecting…';
    case SseConnectionStatus.polling:
      return 'Periodic updates';
  }
}

/// One checkpoint row: exactly the Section 7.2 fields the Section 13.2
/// web feed shows — percent, message, token usage, kind, server time.
class _CheckpointRow extends StatelessWidget {
  const _CheckpointRow({required this.checkpoint});

  final Checkpoint checkpoint;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Padding(
      key: ValueKey<String>('checkpoint-row-${checkpoint.id}'),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Chip(
                key: ValueKey<String>('checkpoint-kind-${checkpoint.id}'),
                label: Text(checkpoint.kind),
                visualDensity: VisualDensity.compact,
              ),
              const Spacer(),
              // Nullable percent: never a fake 0 % (web feed parity).
              Text(
                checkpoint.percent == null
                    ? 'Progress unknown'
                    : '${checkpoint.percent}%',
                key: ValueKey<String>('checkpoint-percent-${checkpoint.id}'),
                style: theme.textTheme.labelLarge,
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            checkpoint.message.isEmpty ? 'No message.' : checkpoint.message,
            key: ValueKey<String>('checkpoint-message-${checkpoint.id}'),
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 2),
          Text(
            _tokenUsageSummary(checkpoint.tokenUsage),
            key: ValueKey<String>('checkpoint-tokens-${checkpoint.id}'),
            style: theme.textTheme.bodySmall
                ?.copyWith(color: theme.colorScheme.outline),
          ),
          Text(
            _serverTime(checkpoint.timestamp),
            key: ValueKey<String>('checkpoint-time-${checkpoint.id}'),
            style: theme.textTheme.bodySmall
                ?.copyWith(color: theme.colorScheme.outline),
          ),
        ],
      ),
    );
  }

  /// Free-form `token_usage` rendered defensively: primitive entries as
  /// `key: value` pairs, unnamed shapes collapse to nothing — no invented
  /// schema (web feed parity; MT-4.6-02 risk note mirrored).
  static String _tokenUsageSummary(JsonObject? usage) {
    final Object? value = usage?.value;
    if (value is! Map) {
      return 'No token usage reported.';
    }
    final List<String> parts = <String>[];
    value.forEach((Object? key, Object? entry) {
      if (entry is num || entry is String || entry is bool) {
        parts.add('$key: $entry');
      }
    });
    return parts.isEmpty ? 'No token usage reported.' : parts.join(' · ');
  }

  /// Server clock rendering (P7): UTC ISO-8601, shortened for the row.
  static String _serverTime(DateTime timestamp) {
    final DateTime utc = timestamp.toUtc();
    String two(int value) => value.toString().padLeft(2, '0');
    return '${utc.year}-${two(utc.month)}-${two(utc.day)} '
        '${two(utc.hour)}:${two(utc.minute)}:${two(utc.second)}Z';
  }
}
