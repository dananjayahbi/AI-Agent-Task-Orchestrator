import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/routes.dart';
import '../../core/api/api_exception.dart';
import '../../core/api/read_error_messages.dart';
import 'notification_history.dart';
import 'notification_preferences.dart';

/// Notifications area (parent plan Section 14.1): exactly the two parts the
/// plan names — "History of alerts, per-event-type toggles" — plus the
/// audit-log entry point MT-5.9-04 places beside it.
///
/// * **History** (MT-5.9-03): the locally recorded receipts of what this
///   app presented (the MT-5.9-02 banner and system-notification taps) —
///   reverse-chronological, loading/empty/error states per Section 20.3,
///   and readable offline because it is a local read (Section 14.2).
/// * **Toggles** (MT-5.9-03): the mobile surface of the MT-5.4-05 backend
///   — opening loads the current set; a change persists through the API
///   and reflects immediately; a failed save restores the prior value and
///   surfaces the error, with the Section 14.2 offline reading (no queued
///   actions). Only the event types the backend defines appear (the list
///   *is* the GET response — no invented types, Section 20.5).
class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() =>
      _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  @override
  void initState() {
    super.initState();
    // Post-frame so first paint is the honest loading state, never a
    // provider read inside build (the review sheet's pattern).
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(notificationHistoryProvider.notifier).ensureLoaded();
      ref.read(notificationPreferencesProvider.notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      // One scroll surface for the whole area (Section 14.1 is two short
      // lists, not two viewports): the history list inside it is
      // shrink-wrapped and non-scrolling — it renders its own rows under
      // the toggles and moves with the page, so small phones never clip
      // the retry affordances or a fourth toggle.
      body: ListView(
        key: const ValueKey<String>('notifications-scroll'),
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'Alert history and per-event-type toggles — one preference '
              'set, shared with the web account settings (Section 13.1).',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          const _PreferencesSection(),
          const Divider(height: 24),
          const _HistorySection(),
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 24),
            child: SizedBox(
              width: double.infinity,
              child: FilledButton.tonalIcon(
                key: const ValueKey<String>('notifications-audit-log-entry'),
                onPressed: () =>
                    Navigator.pushNamed(context, AppArea.auditLog.path),
                icon: const Icon(Icons.history),
                label: const Text('Open audit log'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Display copy for the backend's closed key set — canonical wire strings
/// stay visible (Section 20.5 discipline: display never renames the wire).
(String, String) _preferenceCopy(String eventType) =>
    const <String, (String, String)>{
      'in_human_review': (
        'Review escalations',
        'in_human_review — a task entered human review (any reason).',
      ),
      'merge_failure': (
        'Merge failures',
        'merge_failure — a merge attempt failed and returned to review.',
      ),
      'retry_exhaustion': (
        'Retry exhaustion',
        'retry_exhaustion — a task used up its automatic retries.',
      ),
      'completion_digest': (
        'Completion digest',
        'completion_digest — batched summaries of completed work '
            '(off unless you turn it on).',
      ),
    }[eventType] ??
    (eventType, eventType);

class _PreferencesSection extends ConsumerWidget {
  const _PreferencesSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final NotificationPreferencesState state =
        ref.watch(notificationPreferencesProvider);
    final NotificationPreferencesNotifier notifier =
        ref.read(notificationPreferencesProvider.notifier);
    switch (state.status) {
      case NotificationPreferencesStatus.loading:
        return const Padding(
          key: ValueKey<String>('preferences-loading'),
          padding: EdgeInsets.all(16),
          child: LinearProgressIndicator(),
        );
      case NotificationPreferencesStatus.offline:
        return _PreferencesNotice(
          key: const ValueKey<String>('preferences-offline'),
          message: 'You are offline — notification preferences cannot be '
              'changed right now (nothing is queued).',
          retry: notifier.load,
        );
      case NotificationPreferencesStatus.error:
        return _PreferencesNotice(
          key: const ValueKey<String>('preferences-error'),
          message: friendlyReadErrorMessage(state.error!),
          retry: notifier.load,
        );
      case NotificationPreferencesStatus.ready:
        return Column(
          children: <Widget>[
            for (final NotificationPreferenceItem item in state.items)
              _PreferenceToggle(item: item, state: state),
            if (state.saveError != null)
              _SaveErrorNotice(
                error: state.saveError!,
                onDismiss: notifier.dismissSaveError,
              ),
          ],
        );
    }
  }
}

class _PreferenceToggle extends ConsumerWidget {
  const _PreferenceToggle({required this.item, required this.state});

  final NotificationPreferenceItem item;
  final NotificationPreferencesState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final (String label, String caption) = _preferenceCopy(item.eventType);
    return SwitchListTile(
      key: ValueKey<String>('preference-toggle-${item.eventType}'),
      title: Text(label),
      subtitle: Text(caption),
      value: item.enabled,
      onChanged: state.togglesEnabled
          ? (bool value) => ref
              .read(notificationPreferencesProvider.notifier)
              .setEnabled(item.eventType, value)
          : null,
    );
  }
}

/// Load-failure / offline notice with a retry (the Section 14.2 clear
/// offline state — a failed mutation is never queued).
class _PreferencesNotice extends StatelessWidget {
  const _PreferencesNotice({
    super.key,
    required this.message,
    required this.retry,
  });

  final String message;
  final VoidCallback retry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: <Widget>[
          Expanded(child: Text(message)),
          TextButton(
            key: const ValueKey<String>('preferences-notice-retry'),
            onPressed: retry,
            child: const Text('Try again'),
          ),
        ],
      ),
    );
  }
}

/// A failed save: the prior value is already restored (the notifier); this
/// says why (catalog-friendly copy — Section 9.2 discipline).
class _SaveErrorNotice extends StatelessWidget {
  const _SaveErrorNotice({required this.error, required this.onDismiss});

  final OrchestratorApiException error;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final bool offline = NotificationPreferencesState.isTransportError(error);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        key: const ValueKey<String>('preferences-save-error'),
        children: <Widget>[
          Icon(
            offline ? Icons.cloud_off : Icons.error_outline,
            size: 20,
            color: Theme.of(context).colorScheme.error,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              offline
                  ? 'You are offline — the change was not saved and nothing '
                      'is queued.'
                  : friendlyReadErrorMessage(error),
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
          IconButton(
            key: const ValueKey<String>('preferences-save-error-dismiss'),
            onPressed: onDismiss,
            icon: const Icon(Icons.close),
          ),
        ],
      ),
    );
  }
}

/// Section 14.1's "history of alerts": the locally recorded receipts,
/// newest first (MT-5.9-02 records; this renders).
class _HistorySection extends ConsumerWidget {
  const _HistorySection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final NotificationHistoryState state =
        ref.watch(notificationHistoryProvider);
    switch (state.status) {
      case NotificationHistoryStatus.loading:
        return SizedBox(
          key: const ValueKey<String>('notifications-history-loading'),
          height: 160,
          child: const Center(child: CircularProgressIndicator()),
        );
      case NotificationHistoryStatus.error:
        return Padding(
          key: const ValueKey<String>('notifications-history-error'),
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Text(
                'The local alert history could not be read.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                key: const ValueKey<String>('notifications-history-retry'),
                onPressed: () => ref
                    .read(notificationHistoryProvider.notifier)
                    .ensureLoaded(),
                icon: const Icon(Icons.refresh),
                label: const Text('Try again'),
              ),
            ],
          ),
        );
      case NotificationHistoryStatus.ready:
        if (state.isEmpty) {
          return Padding(
            key: const ValueKey<String>('notifications-history-empty'),
            padding: const EdgeInsets.all(24),
            child: const Text(
              'No alerts yet — what the app presents for you shows up '
              'here.',
              textAlign: TextAlign.center,
            ),
          );
        }
        return ListView.separated(
          key: const ValueKey<String>('notifications-history-list'),
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: state.receipts.length,
          separatorBuilder: (BuildContext context, int index) =>
              const Divider(height: 1),
          itemBuilder: (BuildContext context, int index) {
            final NotificationReceipt receipt = state.receipts[index];
            return ListTile(
              key: ValueKey<String>('history-row-${receipt.dedupeKey}-$index'),
              leading: Icon(
                receipt.origin == NotificationOrigin.banner
                    ? Icons.notifications_active_outlined
                    : Icons.notifications_outlined,
              ),
              title: Text(
                receipt.payload.title.isEmpty
                    ? receipt.payload.eventType
                    : receipt.payload.title,
              ),
              subtitle: Text(
                '${receipt.payload.eventType} · ${receipt.payload.taskId} · '
                '${_formatLocalTime(receipt.recordedAt)}',
              ),
            );
          },
        );
    }
  }
}

/// Local-rendered time (the audit viewer's Section 12.5 reading — a phone
/// shows its own clock, no invented timezones).
String _formatLocalTime(DateTime utc) {
  final DateTime local = utc.toLocal();
  String two(int value) => value.toString().padLeft(2, '0');
  return '${local.year}-${two(local.month)}-${two(local.day)} '
      '${two(local.hour)}:${two(local.minute)}';
}
