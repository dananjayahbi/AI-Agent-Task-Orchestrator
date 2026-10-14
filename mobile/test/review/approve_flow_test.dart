import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/routes.dart';
import 'package:orchestrator_mobile/features/review/review_providers.dart';
import 'package:orchestrator_mobile/features/review/review_screen.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../task_detail/task_detail_test_support.dart';
import 'review_test_support.dart';

/// MT-5.8-04 widget battery: approve-and-merge — Section 14.2's exact
/// confirmation contents, resolution-id binding (including the
/// open-confirmation invalidation), the stale-rejection refresh,
/// double-submit guarding, and the merge-pending outcome (never a
/// premature `completed`).
void main() {
  late FakeReviewRepository repository;

  setUp(() {
    repository = FakeReviewRepository(
      decisionResponse: makeReviewResponse(
        decision: DecisionEnum.approve,
        mergeStatus: 'pending',
        state: 'to_be_audited',
      ),
    )
      ..tasks[reviewTaskId] = makeReviewTask()
      ..resolutions[reviewTaskId] = <Resolution>[makeReviewResolution()]
      ..reports[reviewTaskId] = <AuditReport>[
        makeAuditReport(ruleResults: ruleResultsJson()),
      ]
      ..patches['res-1'] = makePatch(patchBody: '');
  });

  Future<void> pumpReview(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: reviewOverrides(repository: repository),
        child: MaterialApp(
          onGenerateRoute: onGenerateRoute,
          onUnknownRoute: onUnknownRoute,
          home: ReviewScreen(taskId: reviewTaskId),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Future<void> openApproveDialog(WidgetTester tester) async {
    await tester.tap(
      find.byKey(const ValueKey<String>('review-action-approve')),
    );
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('review-approve-confirm')),
      findsOneWidget,
    );
  }

  testWidgets('confirmation shows task id, branch, diff stats and rules',
      (WidgetTester tester) async {
    await pumpReview(tester);
    await openApproveDialog(tester);

    expect(
      find.byKey(const ValueKey<String>('review-approve-task')),
      findsOneWidget,
    );
    expect(find.text(reviewTaskId), findsOneWidget);
    expect(
      find.byKey(const ValueKey<String>('review-approve-branch')),
      findsOneWidget,
    );
    expect(find.text('feat/PID00001-2'), findsOneWidget);
    expect(
      find.byKey(const ValueKey<String>('review-approve-diff-stats')),
      findsOneWidget,
    );
    expect(find.text('2 files · +42 −7'), findsOneWidget,
        reason: 'Section 14.2: diff stats come from the backend summary');
    expect(
      find.byKey(const ValueKey<String>('review-approve-rules-summary')),
      findsOneWidget,
    );
    expect(find.text('2 of 9 rules failed:'), findsOneWidget);

    // Cancel sends nothing.
    await tester.tap(
      find.byKey(const ValueKey<String>('review-approve-cancel')),
    );
    await tester.pumpAndSettle();
    expect(repository.decisionCalls, isEmpty);
  });

  testWidgets('approve binds the viewed resolution id and shows merge-pending',
      (WidgetTester tester) async {
    await pumpReview(tester);
    await openApproveDialog(tester);
    await tester.tap(
      find.byKey(const ValueKey<String>('review-approve-confirm')),
    );
    await tester.pumpAndSettle();

    expect(repository.decisionCalls, hasLength(1));
    final ReviewDecisionRequest request = repository.decisionCalls.single;
    expect(request.decision, DecisionEnum.approve);
    expect(request.resolutionId, 'res-1',
        reason: 'Section 14.2: the decision is bound to the viewed '
            'resolution id');
    expect(request.version, 7,
        reason: 'the optimistic-lock token the sheet rendered (FR-TSK-06)');
    expect(repository.idempotencyKeys.single, isNotEmpty,
        reason: 'ADR-012: one idempotency key per logical decision');

    // Dialog closed; the sheet shows T15's merge-pending sub-status —
    // never a premature completed (ADR-008).
    expect(
      find.byKey(const ValueKey<String>('review-approve-confirm')),
      findsNothing,
    );
    expect(
      find.byKey(const ValueKey<String>('review-outcome-approve-pending')),
      findsOneWidget,
    );
    expect(find.textContaining('merge status: pending'), findsOneWidget,
        reason: 'T15: merge-pending sub-status, never a premature completed');
  });

  testWidgets('a stale approval is rejected, surfaced and refreshed',
      (WidgetTester tester) async {
    repository.nextDecisionError =
        apiError(CodeEnum.VERSION_CONFLICT, statusCode: 409);
    await pumpReview(tester);
    await openApproveDialog(tester);
    await tester.tap(
      find.byKey(const ValueKey<String>('review-approve-confirm')),
    );
    await tester.pumpAndSettle();

    expect(repository.decisionCalls, hasLength(1));
    // The sheet surfaces the rejection in plain language and refreshes.
    expect(
      find.byKey(const ValueKey<String>('review-notice')),
      findsOneWidget,
    );
    expect(
      find.textContaining('against the new resolution'),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-outcome-approve-pending')),
      findsNothing,
      reason: 'a rejected approval records no outcome',
    );
    expect(find.byType(ReviewScreen), findsOneWidget,
        reason: 'the sheet itself is still up (refreshed, not dead)');
  });

  testWidgets(
      'a background re-pin invalidates the open confirmation '
      'before any request leaves', (WidgetTester tester) async {
    await pumpReview(tester);
    final ProviderContainer container = ProviderScope.containerOf(
      tester.element(find.byType(ReviewScreen)),
      listen: false,
    );
    await openApproveDialog(tester);

    // A newer submission arrives while the confirmation sits open.
    repository.resolutions[reviewTaskId] = <Resolution>[
      makeReviewResolution(id: 'res-2', branchName: 'feat/PID00001-3'),
    ];
    await container.read(reviewProvider(reviewTaskId).notifier).load();
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('review-approve-confirm')),
      findsOneWidget,
      reason: 'the dialog is still open on what the user saw',
    );
    expect(find.text('feat/PID00001-2'), findsOneWidget,
        reason: 'the open confirmation still shows the captured branch');

    await tester.tap(
      find.byKey(const ValueKey<String>('review-approve-confirm')),
    );
    await tester.pumpAndSettle();

    expect(repository.decisionCalls, isEmpty,
        reason: 'the stale confirmation never fires a request');
    expect(
      find.byKey(const ValueKey<String>('review-approve-confirm')),
      findsNothing,
      reason: 'the invalid confirmation closes itself',
    );
    expect(
      find.textContaining('against the new resolution'),
      findsOneWidget,
    );
  });

  testWidgets('a double-tap while pending submits exactly once',
      (WidgetTester tester) async {
    await pumpReview(tester);
    final Completer<void> gate = Completer<void>();
    repository.decisionGate = gate;

    await openApproveDialog(tester);
    await tester.tap(
      find.byKey(const ValueKey<String>('review-approve-confirm')),
    );
    await tester.pump();
    // While the request is in flight the confirm button is disabled —
    // a second tap cannot land.
    expect(
      tester
          .widget<FilledButton>(
            find.byKey(const ValueKey<String>('review-approve-confirm')),
          )
          .onPressed,
      isNull,
    );
    await tester.tap(
      find.byKey(const ValueKey<String>('review-approve-confirm')),
      warnIfMissed: false,
    );
    await tester.pump();

    gate.complete();
    await tester.pumpAndSettle();
    expect(repository.decisionCalls, hasLength(1),
        reason: 'P6/ADR-012: never a second submit for one confirmation');
  });
}
