import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/routes.dart';
import 'package:orchestrator_mobile/features/audit_log/audit_log_screen.dart';
import 'package:orchestrator_mobile/features/notifications/notification_history.dart';
import 'package:orchestrator_mobile/features/notifications/notification_preferences.dart';
import 'package:orchestrator_mobile/features/notifications/notifications_screen.dart';
import 'package:orchestrator_mobile/features/task_detail/task_detail_screen.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../board/board_test_support.dart' show makeTask;
import '../notifications/notifications_test_support.dart'
    show
        FakeNotificationPreferencesRepository,
        InMemoryNotificationHistoryStore;
import '../task_detail/task_detail_test_support.dart';
import 'audit_log_test_support.dart';

/// MT-5.9-04 widget battery: the read-only audit log viewer — Section
/// 12.5 essentials in reverse-chronological order, cursor paging per
/// WP-0.5, 1:1 filter wiring (only what `GET /events` supports),
/// loading/empty/error states, row → task detail navigation, and the
/// structural no-mutation assertion.
void main() {
  late FakeAuditLogRepository repository;

  setUp(() {
    repository = FakeAuditLogRepository(
      pages: <ScriptedPage>[
        ScriptedPage(
          <EventEnvelope>[
            makeEvent(id: 1, type: EventEnvelopeTypeEnum.projectPeriodCreated),
            makeEvent(id: 2),
          ],
          'cursor-2',
        ),
        ScriptedPage(
          <EventEnvelope>[
            makeEvent(
              id: 3,
              type: EventEnvelopeTypeEnum.reviewPeriodDecided,
              actorType: EventActorTypeEnum.agent,
              actorRef: 'auditor-1',
            ),
          ],
        ),
      ],
    );
  });

  Future<void> pumpAuditLog(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: auditLogOverrides(repository: repository),
        child: MaterialApp(
          onGenerateRoute: onGenerateRoute,
          onUnknownRoute: onUnknownRoute,
          home: const AuditLogScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets(
      'renders reverse-chronological rows with the Section 12.5 '
      'essentials', (WidgetTester tester) async {
    await pumpAuditLog(tester);

    // Newest first — the accumulated ascending history presented
    // reversed (id 3 on top, id 1 at the bottom).
    expect(find.byKey(const ValueKey<String>('audit-row-3')), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('audit-row-2')), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('audit-row-1')), findsOneWidget);
    expect(
      tester.getTopLeft(find.byKey(const ValueKey<String>('audit-row-3'))).dy,
      lessThan(
        tester.getTopLeft(find.byKey(const ValueKey<String>('audit-row-2'))).dy,
      ),
    );
    expect(
      tester.getTopLeft(find.byKey(const ValueKey<String>('audit-row-2'))).dy,
      lessThan(
        tester.getTopLeft(find.byKey(const ValueKey<String>('audit-row-1'))).dy,
      ),
    );

    // What changed (canonical catalog wire string), actor, ids, time.
    expect(
      find.byKey(const ValueKey<String>('audit-row-type-3')),
      findsOneWidget,
    );
    expect(find.text('review.decided'), findsOneWidget,
        reason: 'Section 9.6 catalog spelling, not the Dart enum name');
    expect(find.text('project.created'), findsOneWidget);
    expect(
      find.byKey(const ValueKey<String>('audit-row-actor-3')),
      findsOneWidget,
    );
    expect(find.text('actor: agent · auditor-1'), findsOneWidget);
    expect(find.text('actor: owner · alice'), findsNWidgets(2));
    expect(
      find.byKey(const ValueKey<String>('audit-row-project-3')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('audit-row-time-3')),
      findsOneWidget,
    );

    // No mutation surface anywhere: no edit affordances exist.
    expect(find.byIcon(Icons.edit_outlined), findsNothing);
    expect(find.byIcon(Icons.delete_outline), findsNothing);
  });

  testWidgets('cursor paging follows next_cursor to the end (WP-0.5)',
      (WidgetTester tester) async {
    await pumpAuditLog(tester);

    expect(repository.calls, hasLength(2), reason: 'both pages were walked');
    expect(repository.calls.first.cursor, isNull);
    expect(repository.calls.first.pageSize, 100);
    expect(repository.calls[1].cursor, 'cursor-2',
        reason: 'the opaque cursor round-trips (pagination.md rule 1)');
    expect(find.byKey(const ValueKey<String>('audit-row-1')), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('audit-row-3')), findsOneWidget);
  });

  testWidgets('filters wire 1:1 to the API parameters and reset pagination',
      (WidgetTester tester) async {
    await pumpAuditLog(tester);
    final int callsBefore = repository.calls.length;

    await tester.enterText(
      find.byKey(const ValueKey<String>('audit-filter-project')),
      'PID00002',
    );
    await tester.enterText(
      find.byKey(const ValueKey<String>('audit-filter-task')),
      'PID00002-T007',
    );
    await tester.tap(
      find.byKey(const ValueKey<String>('audit-filter-apply')),
    );
    await tester.pumpAndSettle();

    expect(repository.calls.length, greaterThan(callsBefore));
    final RecordedFetch filtered = repository.calls.last;
    expect(filtered.project, 'PID00002',
        reason: 'only the parameters GET /events documents');
    expect(filtered.task, 'PID00002-T007');
    expect(filtered.cursor, isNull,
        reason: 'a filter change resets the cursor walk');

    // Active chips with individual clear.
    expect(find.text('project: PID00002'), findsOneWidget);
    expect(find.text('task: PID00002-T007'), findsOneWidget);

    await tester.tap(
      find.byKey(const ValueKey<String>('audit-filter-clear')),
    );
    await tester.pumpAndSettle();
    expect(repository.calls.last.project, isNull);
    expect(repository.calls.last.task, isNull);
    expect(find.text('project: PID00002'), findsNothing);
  });

  testWidgets('an invalid filter fails locally — no request is sent',
      (WidgetTester tester) async {
    await pumpAuditLog(tester);
    final int callsBefore = repository.calls.length;

    await tester.enterText(
      find.byKey(const ValueKey<String>('audit-filter-project')),
      'not-a-pid',
    );
    await tester.tap(
      find.byKey(const ValueKey<String>('audit-filter-apply')),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey<String>('audit-filter-error')),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: find.byKey(const ValueKey<String>('audit-filter-error')),
        matching: find.textContaining('PID00001'),
      ),
      findsOneWidget,
    );
    expect(repository.calls, hasLength(callsBefore),
        reason: 'an invalid filter never reaches the wire');
  });

  testWidgets('empty states are distinct: empty log vs empty results',
      (WidgetTester tester) async {
    repository = FakeAuditLogRepository(
      pages: <ScriptedPage>[const ScriptedPage(<EventEnvelope>[])],
    );
    await pumpAuditLog(tester);
    expect(
      find.byKey(const ValueKey<String>('audit-empty')),
      findsOneWidget,
    );
    expect(find.text('No events recorded yet.'), findsOneWidget);

    await tester.enterText(
      find.byKey(const ValueKey<String>('audit-filter-project')),
      'PID00009',
    );
    await tester.tap(
      find.byKey(const ValueKey<String>('audit-filter-apply')),
    );
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('audit-empty-filters')),
      findsOneWidget,
    );
    expect(find.text('No events match these filters.'), findsOneWidget);
  });

  testWidgets('error renders catalog copy with retry; loading is distinct',
      (WidgetTester tester) async {
    // Park the first fetch so the loading state is observable, and
    // script the failure it resumes into.
    final Completer<void> gate = Completer<void>();
    repository.gate = gate;
    repository.nextError = apiError(CodeEnum.SERVER_ERROR, statusCode: 500);
    await tester.pumpWidget(
      ProviderScope(
        overrides: auditLogOverrides(repository: repository),
        child: MaterialApp(
          onGenerateRoute: onGenerateRoute,
          onUnknownRoute: onUnknownRoute,
          home: const AuditLogScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(
      find.byKey(const ValueKey<String>('audit-loading')),
      findsOneWidget,
    );

    gate.complete();
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('audit-error')),
      findsOneWidget,
    );
    expect(find.textContaining('problem'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey<String>('audit-retry')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('audit-scroll')),
      findsOneWidget,
      reason: 'retry recovers to the list',
    );
  });

  testWidgets(
      'row navigation opens the task detail; zero mutating '
      'requests anywhere', (WidgetTester tester) async {
    final FakeTaskDetailRepository taskDetail = FakeTaskDetailRepository()
      ..tasks['PID00001-T001'] = makeTask(id: 'PID00001-T001');
    await tester.pumpWidget(
      ProviderScope(
        overrides: auditLogOverrides(
          repository: repository,
          taskDetail: taskDetail,
        ),
        child: MaterialApp(
          onGenerateRoute: onGenerateRoute,
          onUnknownRoute: onUnknownRoute,
          home: const AuditLogScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Exercise everything the screen offers: filters, then navigation.
    await tester.enterText(
      find.byKey(const ValueKey<String>('audit-filter-project')),
      'PID00001',
    );
    await tester.tap(
      find.byKey(const ValueKey<String>('audit-filter-apply')),
    );
    await tester.pumpAndSettle();

    await tester.tap(
      find.byKey(const ValueKey<String>('audit-row-task-3')),
    );
    await tester.pumpAndSettle();
    expect(find.byType(TaskDetailScreen), findsOneWidget);
    final TaskDetailScreen detail =
        tester.widget<TaskDetailScreen>(find.byType(TaskDetailScreen));
    expect(detail.taskId, 'PID00001-T001');

    // Structural assertion: the repository interface exposes no
    // mutating method, and every recorded operation is the read.
    expect(repository.operations, isNotEmpty);
    expect(repository.operations.toSet(), <String>{'fetchEvents'},
        reason: 'the viewer performs zero mutating requests (FR-SEC-03)');
  });

  testWidgets('the notifications area offers the audit log entry point',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        // The Notifications screen (MT-5.9-03) loads its history and
        // preferences on mount — the two notification seams ride along
        // with the audit-log one this test already fakes.
        overrides: <Override>[
          ...auditLogOverrides(repository: repository),
          notificationHistoryStoreProvider.overrideWithValue(
            InMemoryNotificationHistoryStore(),
          ),
          notificationPreferencesRepositoryProvider.overrideWithValue(
            FakeNotificationPreferencesRepository(),
          ),
        ],
        child: MaterialApp(
          onGenerateRoute: onGenerateRoute,
          onUnknownRoute: onUnknownRoute,
          home: const NotificationsScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final Finder entry = find.byKey(
      const ValueKey<String>('notifications-audit-log-entry'),
    );
    expect(entry, findsOneWidget,
        reason: 'Section 14.1: the audit log sits beside Notifications');
    await tester.tap(entry);
    await tester.pumpAndSettle();

    expect(find.byType(AuditLogScreen), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('audit-scroll')), findsOneWidget);
  });
}
