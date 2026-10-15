import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/nav_shell.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/notifications/notification_tap_router.dart';
import 'package:orchestrator_mobile/features/notifications/notification_tap_screen.dart';
import 'package:orchestrator_mobile/features/notifications/push_payload.dart';
import 'package:orchestrator_mobile/features/review/review_screen.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart'
    hide DashboardSummary, ProjectDashboardCard;

import '../review/review_test_support.dart';
import 'notifications_test_support.dart';

/// MT-5.9-01 — deep-link routing for notification taps (Section 14.2:
/// "tapping a notification deep-links to the task's review sheet after
/// unlock").
///
/// Covers the plan's WP-5.9 acceptance — the tap lands on the *correct*
/// review sheet in cold and warm start — plus the two structural guarantees
/// around it: **gate precedence** (nothing routes or renders before
/// biometric success) and the **stale fallback** (a task no longer awaiting
/// review degrades to a clear explained state, never a broken sheet), with
/// the MT-5.4-02 payload contract (ids + short title only) pinned by unit
/// cases.
void main() {
  const String taskId = 'PID00001-T001';

  late NotificationsTestHarness harness;

  setUp(() {
    harness = NotificationsTestHarness();
  });

  // --- payload contract (MT-5.4-02 as consumed) -----------------------------

  group('PushTapPayload', () {
    test('parses exactly the five-field allowlist and keys the dedupe tuple',
        () {
      final PushTapPayload? payload = PushTapPayload.tryParse(pushTapData());
      expect(payload, isNotNull);
      expect(payload!.eventType, 'task.transitioned');
      expect(payload.projectId, 'PID00001');
      expect(payload.taskId, taskId);
      expect(payload.taskVersion, 7);
      expect(payload.title, 'Review me');
      // MT-5.4-03's (event type, task id, state version) tuple.
      expect(payload.dedupeKey, 'task.transitioned|$taskId|7');
    });

    test('reads only the allowlisted keys — extras can never ride routing', () {
      final PushTapPayload? payload = PushTapPayload.tryParse(<String, String>{
        ...pushTapData(),
        'review_content': 'the diff and the auditor notes', // never read
        'reason_code': 'audit_escalated',
      });
      expect(payload, isNotNull);
      expect(payload!.dedupeKey, 'task.transitioned|$taskId|7');
    });

    test('fails closed on a partial payload, malformed ids or a bad version',
        () {
      final Map<String, String> full = pushTapData();
      for (final String key in full.keys) {
        final Map<String, String> broken = Map<String, String>.from(full)
          ..remove(key);
        expect(PushTapPayload.tryParse(broken), isNull, reason: key);
      }
      expect(
          PushTapPayload.tryParse(pushTapData(id: 'DROP TABLE tasks')), isNull);
      expect(PushTapPayload.tryParse(pushTapData(projectId: 'PID1')), isNull);
      expect(PushTapPayload.tryParse(pushTapData(version: 'seven')), isNull);
      expect(PushTapPayload.tryParse(pushTapData(version: '-1')), isNull);
    });
  });

  // --- routing (cold, warm, gate ordering, fallback) ------------------------

  testWidgets(
      'cold start: the tap waits through the gate, then unlocks into the '
      'correct review sheet (Section 19 WP-5.9 acceptance)',
      (WidgetTester tester) async {
    await harness.store
        .write(deviceTokenStorageKey, 'tok-cold'); // pragma: allowlist secret
    harness.reviewRepo.tasks[taskId] = makeReviewTask(id: taskId);

    final ProviderContainer container = await harness.pumpApp(tester);
    expect(find.text('Orchestrator is locked'), findsOneWidget);

    // The tap arrives while locked (cold start lands here first).
    final bool accepted = container
        .read(pendingNotificationTapProvider.notifier)
        .report(pushTapData());
    expect(accepted, isTrue);
    await tester.pump();
    expect(find.byType(NotificationTapScreen), findsNothing,
        reason: 'gate precedence: nothing routes before unlock');
    expect(find.byType(ReviewScreen), findsNothing);
    expect(container.read(pendingNotificationTapProvider), isNotNull);

    // Park the resolution fetch so the standard loading state is observable.
    // Unlock without settling first: the loading spinner animates until the
    // destination resolves (pumpAndSettle would spin with it).
    final Completer<void> gate = Completer<void>();
    harness.reviewRepo.gate = gate;
    await tester.tap(find.text('Unlock'));
    await tester.pump();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(
        find.byKey(const ValueKey<String>('deeplink-loading')), findsOneWidget);
    expect(find.byType(ReviewScreen), findsNothing);

    gate.complete();
    await tester.pumpAndSettle();

    expect(find.byType(NotificationTapScreen), findsNothing,
        reason: 'the picker replaces itself with the destination');
    expect(find.byType(ReviewScreen), findsOneWidget);
    expect(find.text('Review sheet'), findsOneWidget);
    expect(harness.reviewRepo.tasks.keys, contains(taskId));
    expect(container.read(pendingNotificationTapProvider), isNull,
        reason: 'the tap was consumed exactly once');
    await harness.endLocked(tester, container);
  });

  testWidgets(
      'warm start (already unlocked): a fresh tap routes straight through',
      (WidgetTester tester) async {
    await harness.store
        .write(deviceTokenStorageKey, 'tok-warm'); // pragma: allowlist secret
    harness.reviewRepo.tasks[taskId] = makeReviewTask(id: taskId);

    final ProviderContainer container = await harness.pumpApp(tester);
    await harness.unlock(tester);
    expect(find.byType(NavShell), findsOneWidget,
        reason: 'warm start begins in the unlocked shell');

    container
        .read(pendingNotificationTapProvider.notifier)
        .report(pushTapData());
    await tester.pumpAndSettle();

    expect(find.byType(ReviewScreen), findsOneWidget);
    expect(find.text('Review sheet'), findsOneWidget);
    await harness.endLocked(tester, container);
  });

  testWidgets(
      'a malformed payload routes nowhere — an honest no-op, never a guess',
      (WidgetTester tester) async {
    final ProviderContainer container = await harness.pumpApp(tester);
    expect(find.byType(NavShell), findsOneWidget);

    final bool accepted = container
        .read(pendingNotificationTapProvider.notifier)
        .report(<String, String>{'event_type': 'task.transitioned'});
    await tester.pumpAndSettle();

    expect(accepted, isFalse);
    expect(container.read(pendingNotificationTapProvider), isNull);
    expect(find.byType(NotificationTapScreen), findsNothing);
    expect(find.byType(ReviewScreen), findsNothing);
    expect(find.byType(NavShell), findsOneWidget);
  });

  testWidgets(
      'stale tap: a task no longer in review degrades to the explained '
      'state with a way home — never a broken sheet',
      (WidgetTester tester) async {
    harness.reviewRepo.tasks[taskId] =
        makeReviewTask(id: taskId, state: StateEnum.pending);

    final ProviderContainer container = await harness.pumpApp(tester);
    container
        .read(pendingNotificationTapProvider.notifier)
        .report(pushTapData());
    await tester.pumpAndSettle();

    expect(find.byType(ReviewScreen), findsNothing);
    expect(
        find.byKey(const ValueKey<String>('deeplink-stale')), findsOneWidget);
    expect(find.textContaining('no longer actionable'), findsOneWidget);
    expect(find.textContaining('Nothing was changed'), findsOneWidget);

    await tester.tap(find.text('Go to home'));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey<String>('deeplink-stale')), findsNothing);
    expect(find.byType(NavShell), findsOneWidget,
        reason: 'the fallback lands on home, explained — not a dead end');
  });

  testWidgets(
      'a deleted task (TASK_NOT_FOUND) takes the same stale fallback path',
      (WidgetTester tester) async {
    final ProviderContainer container = await harness.pumpApp(tester);
    // Nothing scripted in the fake: fetchTask answers TASK_NOT_FOUND.
    container
        .read(pendingNotificationTapProvider.notifier)
        .report(pushTapData());
    await tester.pumpAndSettle();

    expect(
        find.byKey(const ValueKey<String>('deeplink-stale')), findsOneWidget);
    expect(find.byType(ReviewScreen), findsNothing);
  });

  testWidgets(
      'an unreachable server shows the honest error state with retry — '
      'no destination is guessed', (WidgetTester tester) async {
    harness.reviewRepo.tasks[taskId] = makeReviewTask(id: taskId);
    harness.reviewRepo.nextTaskError = offlineError();

    final ProviderContainer container = await harness.pumpApp(tester);
    container
        .read(pendingNotificationTapProvider.notifier)
        .report(pushTapData());
    await tester.pumpAndSettle();

    expect(
        find.byKey(const ValueKey<String>('deeplink-error')), findsOneWidget);
    expect(find.byType(ReviewScreen), findsNothing);

    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(find.byType(ReviewScreen), findsOneWidget,
        reason: 'retry after connectivity returns opens the sheet');
  });
}
