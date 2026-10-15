import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/app.dart';
import 'package:orchestrator_mobile/app/nav_shell.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/notifications/foreground_banner.dart';
import 'package:orchestrator_mobile/features/notifications/notification_history.dart';
import 'package:orchestrator_mobile/features/notifications/notification_tap_router.dart';
import 'package:orchestrator_mobile/features/review/review_screen.dart';

import '../review/review_test_support.dart';
import 'notifications_test_support.dart';

/// MT-5.9-02 — the foreground banner (Section 14.2: "Foreground messages
/// display an in-app banner"): payload-content-only rendering, banner tap =
/// notification tap (reusing MT-5.9-01's routing), MT-5.4-03 dedupe (never
/// twice), nothing sensitive while locked, the recorded dismissal rule
/// (tap to act or auto-dismiss after 6 s), and receipt recording for
/// MT-5.9-03's history.
void main() {
  const String taskId = 'PID00001-T001';

  late NotificationsTestHarness harness;

  setUp(() {
    harness = NotificationsTestHarness();
  });

  Future<void> unlockApp(WidgetTester tester) async {
    await harness.store
        .write(deviceTokenStorageKey, 'tok-banner'); // pragma: allowlist secret
    await harness.pumpApp(tester);
    await harness.unlock(tester);
    expect(find.text('Home / Overview'), findsOneWidget);
  }

  testWidgets(
      'a foregrounded message renders the banner with payload content only '
      '(short title + canonical event type — nothing fetched)',
      (WidgetTester tester) async {
    await unlockApp(tester);
    final ProviderContainer container =
        ProviderScope.containerOf(tester.element(find.byType(OrchestratorApp)));

    final bool presented = container
        .read(foregroundPushHandlerProvider.notifier)
        .present(pushTapData(title: 'Fix login redirect'));
    expect(presented, isTrue);
    await tester.pump();

    expect(find.byKey(const ValueKey<String>('foreground-banner')),
        findsOneWidget);
    final Iterable<Text> bannerTexts = tester
        .widgetList<Text>(find.descendant(
          of: find.byKey(const ValueKey<String>('foreground-banner')),
          matching: find.byType(Text),
        ))
        .toList();
    expect(
      bannerTexts.map((Text t) => t.data).toList(),
      <String>['Fix login redirect', 'task.transitioned'],
      reason: 'exactly the MT-5.4-02 payload strings — no enriched content',
    );
    // The banner rides above the shell without replacing it.
    expect(find.byType(NavShell), findsOneWidget);

    await harness.endLocked(tester, container);
  });

  testWidgets(
      'banner tap routes exactly like a notification tap → review sheet',
      (WidgetTester tester) async {
    harness.reviewRepo.tasks[taskId] = makeReviewTask(id: taskId);
    await unlockApp(tester);
    final ProviderContainer container =
        ProviderScope.containerOf(tester.element(find.byType(OrchestratorApp)));

    container
        .read(foregroundPushHandlerProvider.notifier)
        .present(pushTapData());
    await tester.pump();
    expect(find.byKey(const ValueKey<String>('foreground-banner')),
        findsOneWidget);

    await tester
        .tap(find.byKey(const ValueKey<String>('foreground-banner-tap')));
    await tester.pumpAndSettle();

    expect(
        find.byKey(const ValueKey<String>('foreground-banner')), findsNothing);
    expect(find.byType(ReviewScreen), findsOneWidget);
    expect(find.text('Review sheet'), findsOneWidget);

    await harness.endLocked(tester, container);
  });

  testWidgets(
      'a duplicate message never renders a second banner (MT-5.4-03 keys)',
      (WidgetTester tester) async {
    await unlockApp(tester);
    final ProviderContainer container =
        ProviderScope.containerOf(tester.element(find.byType(OrchestratorApp)));
    final ForegroundPushHandler handler =
        container.read(foregroundPushHandlerProvider.notifier);

    expect(handler.present(pushTapData()), isTrue);
    expect(handler.present(pushTapData()), isFalse,
        reason: 'the same (event type, task id, state version) key');
    await tester.pump();

    expect(find.byKey(const ValueKey<String>('foreground-banner')),
        findsOneWidget);

    await harness.endLocked(tester, container);
  });

  testWidgets(
      'while the gate is locked nothing is presented — no sensitive '
      'content, no receipt, no key consumed', (WidgetTester tester) async {
    await harness.store
        .write(deviceTokenStorageKey, 'tok-locked'); // pragma: allowlist secret
    final ProviderContainer container = await harness.pumpApp(tester);
    expect(find.text('Orchestrator is locked'), findsOneWidget);

    final bool presented = container
        .read(foregroundPushHandlerProvider.notifier)
        .present(pushTapData());
    await tester.pumpAndSettle();

    expect(presented, isFalse);
    expect(
        find.byKey(const ValueKey<String>('foreground-banner')), findsNothing);
    expect(find.text('Review me'), findsNothing);
    expect(container.read(presentedPushKeysProvider), isEmpty);
    expect(harness.historyStore.loadCalls, 0,
        reason: 'nothing was presented, so nothing is recorded');
  });

  testWidgets(
      'an untouched banner auto-dismisses after the recorded delay — '
      'and the alert stays in history', (WidgetTester tester) async {
    await unlockApp(tester);
    final ProviderContainer container =
        ProviderScope.containerOf(tester.element(find.byType(OrchestratorApp)));

    container
        .read(foregroundPushHandlerProvider.notifier)
        .present(pushTapData());
    await tester.pump();
    expect(find.byKey(const ValueKey<String>('foreground-banner')),
        findsOneWidget);

    await tester.pump(foregroundBannerDuration);
    await tester.pumpAndSettle();

    expect(
        find.byKey(const ValueKey<String>('foreground-banner')), findsNothing);
    expect(container.read(activeBannerProvider), isNull);

    final NotificationHistoryState history =
        container.read(notificationHistoryProvider);
    expect(history.status, NotificationHistoryStatus.ready);
    expect(history.receipts.single.origin, NotificationOrigin.banner);
    expect(history.receipts.single.payload.taskId, taskId);

    await harness.endLocked(tester, container);
  });

  testWidgets(
      'a system-notification tap records its receipt and stops the '
      'same event re-presenting as a banner', (WidgetTester tester) async {
    harness.reviewRepo.tasks[taskId] = makeReviewTask(id: taskId);
    await unlockApp(tester);
    final ProviderContainer container =
        ProviderScope.containerOf(tester.element(find.byType(OrchestratorApp)));

    container
        .read(pendingNotificationTapProvider.notifier)
        .report(pushTapData());
    await tester.pumpAndSettle();
    expect(find.byType(ReviewScreen), findsOneWidget);

    final NotificationHistoryState history =
        container.read(notificationHistoryProvider);
    expect(
        history.receipts.single.origin, NotificationOrigin.systemNotification);
    expect(history.receipts.single.dedupeKey, 'task.transitioned|$taskId|7');

    expect(
      container
          .read(foregroundPushHandlerProvider.notifier)
          .present(pushTapData()),
      isFalse,
      reason: 'already presented — banner and system notification never double',
    );
    await tester.pump();
    expect(
        find.byKey(const ValueKey<String>('foreground-banner')), findsNothing);

    await harness.endLocked(tester, container);
  });
}
