import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/features/notifications/notification_history.dart';
import 'package:orchestrator_mobile/features/notifications/notifications_screen.dart';
import 'package:orchestrator_mobile/features/notifications/push_payload.dart';

import '../dashboard/dashboard_test_support.dart'
    show catalogError, transportError;
import 'notifications_test_support.dart';

/// MT-5.9-03 — the Notifications screen (Section 14.1: "History of alerts,
/// per-event-type toggles"): receipt rendering from fixtures with the
/// loading/empty/error states, toggle load/save/failure paths against the
/// MT-5.4-05 backend seam (only the types it defines), and the Section 14.2
/// offline refusal with nothing queued.
void main() {
  late NotificationsTestHarness harness;

  setUp(() {
    harness = NotificationsTestHarness();
  });

  NotificationReceipt receipt({
    required String taskId,
    required String title,
    NotificationOrigin origin = NotificationOrigin.banner,
    DateTime? recordedAt,
    String eventType = 'task.transitioned',
  }) =>
      NotificationReceipt(
        payload: PushTapPayload.tryParse(
          pushTapData(id: taskId, title: title, eventType: eventType),
        )!,
        origin: origin,
        recordedAt: recordedAt ?? DateTime.utc(2026, 10, 11, 12, 45),
      );

  Future<ProviderContainer> pumpScreen(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: harness.overrides(),
        child: const MaterialApp(home: NotificationsScreen()),
      ),
    );
    await tester.pumpAndSettle();
    return ProviderScope.containerOf(
      tester.element(find.byType(NotificationsScreen)),
    );
  }

  // --- history ---------------------------------------------------------------

  testWidgets('history renders receipts newest-first: type, task and time',
      (WidgetTester tester) async {
    harness.historyStore.rows.addAll(<NotificationReceipt>[
      receipt(
        taskId: 'PID00001-T002',
        title: 'Escalation two',
        origin: NotificationOrigin.systemNotification,
        recordedAt: DateTime.utc(2026, 10, 11, 13, 45),
      ),
      receipt(taskId: 'PID00001-T001', title: 'Escalation one'),
    ]);

    await pumpScreen(tester);

    expect(find.byKey(const ValueKey<String>('notifications-history-list')),
        findsOneWidget);
    expect(find.text('Escalation two'), findsOneWidget);
    expect(find.text('Escalation one'), findsOneWidget);
    // The Section 14.1 trio: per-event type, task reference, local time.
    expect(
      find.textContaining('task.transitioned · PID00001-T002 · '),
      findsOneWidget,
    );
    expect(
      find.textContaining('task.transitioned · PID00001-T001 · '),
      findsOneWidget,
    );
    final double newerY = tester.getTopLeft(find.text('Escalation two')).dy;
    final double olderY = tester.getTopLeft(find.text('Escalation one')).dy;
    expect(newerY, lessThan(olderY), reason: 'reverse-chronological');
  });

  testWidgets('the history shows its loading state until the store answers',
      (WidgetTester tester) async {
    final Completer<void> gate = Completer<void>();
    harness.historyStore.gate = gate;

    await tester.pumpWidget(
      ProviderScope(
        overrides: harness.overrides(),
        child: const MaterialApp(home: NotificationsScreen()),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.byKey(const ValueKey<String>('notifications-history-loading')),
        findsOneWidget);
    expect(find.byKey(const ValueKey<String>('notifications-history-list')),
        findsNothing);

    gate.complete();
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey<String>('notifications-history-empty')),
        findsOneWidget);
  });

  testWidgets('an empty history says so honestly (Section 20.3)',
      (WidgetTester tester) async {
    await pumpScreen(tester);

    expect(find.byKey(const ValueKey<String>('notifications-history-empty')),
        findsOneWidget);
    expect(find.textContaining('No alerts yet'), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('notifications-history-list')),
        findsNothing);
  });

  testWidgets(
      'an unreadable local history surfaces an error with a retry '
      'that recovers', (WidgetTester tester) async {
    harness.historyStore.failLoads = true;

    await pumpScreen(tester);

    expect(find.byKey(const ValueKey<String>('notifications-history-error')),
        findsOneWidget);
    expect(find.textContaining('could not be read'), findsOneWidget);

    harness.historyStore.failLoads = false;
    await tester
        .tap(find.byKey(const ValueKey<String>('notifications-history-retry')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey<String>('notifications-history-empty')),
        findsOneWidget);
    expect(find.byKey(const ValueKey<String>('notifications-history-error')),
        findsNothing);
  });

  // --- toggles (the MT-5.4-05 backend surface) -------------------------------

  testWidgets(
      'toggles mirror exactly the set the backend defines — no '
      'invented types (Section 20.5)', (WidgetTester tester) async {
    await pumpScreen(tester);

    expect(find.byType(SwitchListTile), findsNWidgets(4));
    for (final String key in const <String>[
      'in_human_review',
      'merge_failure',
      'retry_exhaustion',
      'completion_digest',
    ]) {
      expect(find.byKey(ValueKey<String>('preference-toggle-$key')),
          findsOneWidget);
    }
    // OQ-13 defaults as the backend served them: escalations on, digest off.
    final SwitchListTile escalation = tester.widget<SwitchListTile>(
      find.byKey(const ValueKey<String>('preference-toggle-in_human_review')),
    );
    final SwitchListTile digest = tester.widget<SwitchListTile>(
      find.byKey(const ValueKey<String>('preference-toggle-completion_digest')),
    );
    expect(escalation.value, isTrue);
    expect(digest.value, isFalse);
  });

  testWidgets('a toggle persists through the API and reflects immediately',
      (WidgetTester tester) async {
    final Completer<void> gate = Completer<void>();
    harness.prefsRepo.gate = gate;

    await pumpScreen(tester);
    await tester.tap(
        find.byKey(const ValueKey<String>('preference-toggle-merge_failure')));
    await tester.pump();

    // Optimistic value, locked while the save is in flight (one at a time).
    final SwitchListTile saving = tester.widget<SwitchListTile>(
      find.byKey(const ValueKey<String>('preference-toggle-merge_failure')),
    );
    expect(saving.value, isFalse);
    expect(saving.onChanged, isNull);

    gate.complete();
    await tester.pumpAndSettle();

    expect(harness.prefsRepo.updates, <(String, bool)>[
      ('merge_failure', false),
    ]);
    final SwitchListTile settled = tester.widget<SwitchListTile>(
      find.byKey(const ValueKey<String>('preference-toggle-merge_failure')),
    );
    expect(settled.value, isFalse);
    expect(settled.onChanged, isNotNull);
  });

  testWidgets(
      'a failed save restores the prior value and surfaces a '
      'catalog-friendly error (raw server text never shown)',
      (WidgetTester tester) async {
    harness.prefsRepo.nextUpdateError = catalogError();

    await pumpScreen(tester);
    await tester.tap(
        find.byKey(const ValueKey<String>('preference-toggle-merge_failure')));
    await tester.pumpAndSettle();

    final SwitchListTile restored = tester.widget<SwitchListTile>(
      find.byKey(const ValueKey<String>('preference-toggle-merge_failure')),
    );
    expect(restored.value, isTrue, reason: 'the previous value is back');
    expect(find.byKey(const ValueKey<String>('preferences-save-error')),
        findsOneWidget);
    expect(find.textContaining('raw server detail'), findsNothing);
    expect(find.textContaining('server had a problem'), findsOneWidget);

    await tester.tap(
        find.byKey(const ValueKey<String>('preferences-save-error-dismiss')));
    await tester.pump();
    expect(find.byKey(const ValueKey<String>('preferences-save-error')),
        findsNothing);
  });

  testWidgets(
      'offline: the save refuses with the clear state and nothing '
      'is queued (Section 14.2)', (WidgetTester tester) async {
    harness.prefsRepo.nextUpdateError = transportError();

    await pumpScreen(tester);
    await tester.tap(find
        .byKey(const ValueKey<String>('preference-toggle-retry_exhaustion')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey<String>('preferences-save-error')),
        findsOneWidget);
    expect(find.textContaining('offline — the change was not saved'),
        findsOneWidget);
    expect(find.textContaining('nothing is queued'), findsOneWidget);
    final SwitchListTile restored = tester.widget<SwitchListTile>(
      find.byKey(const ValueKey<String>('preference-toggle-retry_exhaustion')),
    );
    expect(restored.value, isTrue);

    // One attempted request, ever — no automatic retry, no queue.
    await tester.pump(const Duration(seconds: 5));
    expect(harness.prefsRepo.updates, hasLength(1));
  });

  testWidgets('offline on load: the section states it plainly with a retry',
      (WidgetTester tester) async {
    harness.prefsRepo.nextFetchError = transportError();

    await pumpScreen(tester);

    expect(find.byKey(const ValueKey<String>('preferences-offline')),
        findsOneWidget);
    expect(find.textContaining('preferences cannot be changed right now'),
        findsOneWidget);
    expect(find.byType(SwitchListTile), findsNothing);

    await tester
        .tap(find.byKey(const ValueKey<String>('preferences-notice-retry')));
    await tester.pumpAndSettle();

    expect(find.byType(SwitchListTile), findsNWidgets(4),
        reason: 'retry after connectivity returns loads the set');
  });

  // --- the MT-5.9-04 entry point stays ---------------------------------------

  testWidgets('the audit-log entry point remains beside Notifications',
      (WidgetTester tester) async {
    await pumpScreen(tester);

    expect(
      find.byKey(const ValueKey<String>('notifications-audit-log-entry')),
      findsOneWidget,
    );
  });
}
