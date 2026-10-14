import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/routes.dart';
import 'package:orchestrator_mobile/features/board/board_screen.dart';
import 'package:orchestrator_mobile/features/review/review_screen.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../board/board_test_support.dart';
import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';
import '../task_detail/task_detail_test_support.dart';
import 'review_test_support.dart';

/// MT-5.8-01 widget battery: the review sheet layout — every Section
/// 14.1 region, canonical reasons with friendly labels, the four
/// Section 20.3 states (including the Section 14.2 offline state that
/// disables mutations), id-based addressing, and the board entry point.
void main() {
  late FakeReviewRepository repository;

  setUp(() {
    repository = FakeReviewRepository()
      ..tasks[reviewTaskId] = makeReviewTask()
      ..resolutions[reviewTaskId] = <Resolution>[makeReviewResolution()]
      ..reports[reviewTaskId] = <AuditReport>[
        makeAuditReport(ruleResults: ruleResultsJson()),
      ]
      ..patches['res-1'] = makePatch(patchBody: '');
  });

  Future<void> pumpReview(
    WidgetTester tester, {
    String? taskId = reviewTaskId,
    bool settle = true,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: reviewOverrides(repository: repository),
        child: MaterialApp(
          onGenerateRoute: onGenerateRoute,
          onUnknownRoute: onUnknownRoute,
          home: ReviewScreen(taskId: taskId),
        ),
      ),
    );
    if (settle) {
      await tester.pumpAndSettle();
    } else {
      // Loading spinner animates forever — pump frames only.
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  /// Unmounts the tree so the next [pumpReview] builds a fresh
  /// ProviderScope (and a fresh notifier load).
  Future<void> resetTree(WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: SizedBox.shrink()),
    );
  }

  /// The enabled/disabled state of one of the action-bar buttons.
  bool? actionEnabled(WidgetTester tester, String key) {
    final Finder finder = find.byKey(ValueKey<String>(key));
    final ButtonStyleButton button = tester.widget<ButtonStyleButton>(finder);
    return button.onPressed != null;
  }

  testWidgets('renders every Section 14.1 region with the fixed action bar',
      (WidgetTester tester) async {
    // A tall surface so every region is inside the initial viewport
    // (the sheet is one long scroll — laziness is the diff region's
    // own test, not this layout battery).
    tester.view.physicalSize = const Size(1080, 2600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await pumpReview(tester);

    // Regions, in plan order (reason + rule results, execution summary,
    // auditor notes, diff).
    expect(find.text('Escalation reason'), findsOneWidget);
    expect(
      find.byKey(const ValueKey<String>('review-reason-canonical')),
      findsOneWidget,
    );
    expect(find.text('Rule results'), findsOneWidget);
    expect(find.text('Execution summary'), findsOneWidget);
    expect(
      find.byKey(const ValueKey<String>('review-execution-summary')),
      findsOneWidget,
    );
    expect(find.text('Auditor notes'), findsOneWidget);
    expect(find.text('Evidence'), findsOneWidget);
    expect(find.text('Diff'), findsOneWidget);

    // Three actions, always reachable above the safe area.
    expect(
      find.byKey(const ValueKey<String>('review-actions-bar')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-action-approve')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-action-request-changes')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-action-reassign')),
      findsOneWidget,
    );
    expect(actionEnabled(tester, 'review-action-approve'), isTrue);

    // Canonical Section 8.4 string retained with its friendly label
    // (ADR-010; Sections 8.4, 20.5).
    expect(
      find.text('test_failure'),
      findsOneWidget,
      reason: 'the canonical Section 8.4 string stays visible',
    );
    expect(
      find.text('Tests failed or produced no evidence'),
      findsOneWidget,
      reason: 'friendly label rendered alongside the canonical value',
    );
  });

  testWidgets('loading state shows the spinner with every action disabled',
      (WidgetTester tester) async {
    final Completer<void> held = Completer<void>();
    repository.gate = held;
    await pumpReview(tester, settle: false);
    expect(
      find.byKey(const ValueKey<String>('review-loading')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-actions-bar')),
      findsOneWidget,
      reason: 'the bar exists but every action is disabled while loading',
    );
    expect(actionEnabled(tester, 'review-action-approve'), isFalse);
    held.complete();
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('review-loading')),
      findsNothing,
    );
  });

  testWidgets('catalog error renders the honest error state with retry',
      (WidgetTester tester) async {
    repository.nextTaskError = apiError(CodeEnum.SERVER_ERROR, statusCode: 500);
    await resetTree(tester);
    await pumpReview(tester);
    expect(
      find.byKey(const ValueKey<String>('review-error')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-retry')),
      findsOneWidget,
    );
    expect(find.text('Rule results'), findsNothing,
        reason: 'no fabricated sheet behind an error');
  });

  testWidgets('offline shows the clear Section 14.2 state; nothing queues',
      (WidgetTester tester) async {
    repository.nextTaskError = offlineError();
    await resetTree(tester);
    await pumpReview(tester);

    expect(
      find.byKey(const ValueKey<String>('review-offline')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-offline-copy')),
      findsOneWidget,
    );
    expect(actionEnabled(tester, 'review-action-approve'), isFalse);
    expect(actionEnabled(tester, 'review-action-request-changes'), isFalse);
    expect(actionEnabled(tester, 'review-action-reassign'), isFalse);
    expect(
      repository.decisionCalls,
      isEmpty,
      reason: 'offline never queues a decision (Section 14.2)',
    );
  });

  testWidgets('missing audit report degrades to reason + summary',
      (WidgetTester tester) async {
    repository.reports[reviewTaskId] = <AuditReport>[];
    await resetTree(tester);
    await pumpReview(tester);

    expect(
      find.byKey(const ValueKey<String>('review-report-missing')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-rules-missing')),
      findsNothing,
      reason: 'no report means no rule table at all — never a fake one',
    );
    expect(
      find.byKey(const ValueKey<String>('review-execution-summary')),
      findsOneWidget,
      reason: 'execution summary still renders (Section 8.5 path)',
    );
    expect(find.text('Evidence'), findsNothing);
  });

  testWidgets('no task id renders the honest empty state',
      (WidgetTester tester) async {
    await resetTree(tester);
    await pumpReview(tester, taskId: null);
    expect(
      find.byKey(const ValueKey<String>('review-no-task')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-actions-bar')),
      findsNothing,
    );
  });

  testWidgets('the /review route is id-addressed (contract for WP-5.9)',
      (WidgetTester tester) async {
    late BuildContext host;
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (BuildContext context) {
            host = context;
            return const SizedBox.shrink();
          },
        ),
      ),
    );
    final Route<dynamic> withId = onGenerateRoute(
      const RouteSettings(name: '/review', arguments: 'PID00001-T009'),
    );
    expect(withId, isA<MaterialPageRoute<dynamic>>());
    final Widget built = (withId as MaterialPageRoute<dynamic>).builder(host);
    expect(built, isA<ReviewScreen>());
    expect((built as ReviewScreen).taskId, 'PID00001-T009');

    final Route<dynamic> bare = onGenerateRoute(
      const RouteSettings(name: '/review'),
    );
    final Widget bareBuilt = (bare as MaterialPageRoute<dynamic>).builder(host);
    expect((bareBuilt as ReviewScreen).taskId, isNull,
        reason: 'no id → the honest empty state, never a fabricated sheet');
  });

  testWidgets('the board hands an escalated card off to the sheet by id',
      (WidgetTester tester) async {
    repository.tasks['PID00001-T1'] =
        makeTask(id: 'PID00001-T1', state: StateEnum.inHumanReview);
    final FakeProjectsRepository projects = FakeProjectsRepository()
      ..projects = <Project>[makeProject(id: 'PID00001', name: 'Solo')];
    final FakeBoardRepository board = FakeBoardRepository()
      ..tasksByProject['PID00001'] = <Task>[
        makeTask(id: 'PID00001-T1', state: StateEnum.inHumanReview),
      ];
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          ...boardOverrides(
            projects: projects,
            board: board,
            cache: InMemoryJsonCache(),
            sseClient: buildTestSseClient(transport: FakeSseTransport()),
          ),
          ...reviewOverrides(repository: repository),
        ],
        child: MaterialApp(
          onGenerateRoute: onGenerateRoute,
          onUnknownRoute: onUnknownRoute,
          home: const BoardScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Jump to the in_human_review page (index 4) — the card lives there.
    await tester.tap(find.byKey(const ValueKey<String>('board-page-chip-4')));
    await tester.pumpAndSettle();

    final Finder entry = find.byKey(
      const ValueKey<String>('board-card-review-PID00001-T1'),
    );
    expect(entry, findsOneWidget,
        reason: 'the needs-review affordance exists on escalated cards');
    await tester.tap(entry);
    await tester.pumpAndSettle();

    expect(find.byType(ReviewScreen), findsOneWidget);
    expect(find.text('Escalation reason'), findsOneWidget);
    final ReviewScreen sheet = tester.widget<ReviewScreen>(
      find.byType(ReviewScreen),
    );
    expect(sheet.taskId, 'PID00001-T1');
  });
}
