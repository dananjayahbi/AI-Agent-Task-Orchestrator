import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/routes.dart';
import 'package:orchestrator_mobile/features/review/review_screen.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../task_detail/task_detail_test_support.dart';
import 'review_test_support.dart';

/// MT-5.8-06 widget battery: reassign — the plain-language confirmation
/// (Section 11.5 / T16), the optional note, the absence of any
/// assignee picker (free re-claim), and the distinct payload that
/// separates it from request-changes.
void main() {
  late FakeReviewRepository repository;

  setUp(() {
    repository = FakeReviewRepository(
      decisionResponse: makeReviewResponse(
        decision: DecisionEnum.reassign,
        state: 'pending',
        mergeStatus: 'none',
        version: 8,
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

  Future<void> openReassign(WidgetTester tester) async {
    await tester.tap(
      find.byKey(const ValueKey<String>('review-action-reassign')),
    );
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('review-reassign-copy')),
      findsOneWidget,
    );
  }

  testWidgets(
      'confirmation states the T16 outcome with an optional note '
      'and no assignee picker', (WidgetTester tester) async {
    await pumpReview(tester);
    await openReassign(tester);

    // Plain-language outcome (Sections 11.5, 8.2).
    expect(
      find.text(
        'The task returns to pending and the current worker is cleared, '
        'so any eligible agent may claim it.',
      ),
      findsOneWidget,
    );

    // The note is optional — submission is enabled with an empty field.
    expect(
      find.byKey(const ValueKey<String>('review-reassign-note-field')),
      findsOneWidget,
    );
    expect(
      tester
          .widget<FilledButton>(
            find.byKey(const ValueKey<String>('review-reassign-confirm')),
          )
          .onPressed,
      isNotNull,
      reason: 'only request changes requires a note (Section 8.2 T16)',
    );

    // No assignee picker exists anywhere in the dialog (Sections 11.5,
    // 8.2 — reassign means free re-claim; nothing invented).
    expect(find.byType(DropdownButtonFormField<Object>), findsNothing);
    expect(find.byType(Autocomplete<Object>), findsNothing);
    expect(find.textContaining('Assign to'), findsNothing);

    // Cancel sends nothing.
    await tester.tap(
      find.byKey(const ValueKey<String>('review-reassign-cancel')),
    );
    await tester.pumpAndSettle();
    expect(repository.decisionCalls, isEmpty);
  });

  testWidgets('reassign with no note sends the explicit reassign payload',
      (WidgetTester tester) async {
    await pumpReview(tester);
    await openReassign(tester);
    await tester.tap(
      find.byKey(const ValueKey<String>('review-reassign-confirm')),
    );
    await tester.pumpAndSettle();

    expect(repository.decisionCalls, hasLength(1));
    final ReviewDecisionRequest request = repository.decisionCalls.single;
    expect(request.decision, DecisionEnum.reassign,
        reason: 'never ambiguous with request_changes (risk note)');
    expect(request.note, isEmpty,
        reason: 'the note is optional — empty stays empty');
    expect(request.version, 7);
    expect(request.resolutionId, isNull,
        reason: 'only approve binds a resolution id');

    // T16 outcome: back to pending, decision recorded (canonical wire
    // value on display).
    expect(
      find.byKey(const ValueKey<String>('review-outcome-reassign')),
      findsOneWidget,
    );
    expect(
      find.textContaining('reassign recorded — task is now pending'),
      findsOneWidget,
    );
    expect(
      find.textContaining('worker was cleared'),
      findsOneWidget,
    );
  });

  testWidgets('an optional note rides along when provided',
      (WidgetTester tester) async {
    await pumpReview(tester);
    await openReassign(tester);
    await tester.enterText(
      find.byKey(const ValueKey<String>('review-reassign-note-field')),
      'Take two on the flaky test',
    );
    await tester.pump();
    await tester.tap(
      find.byKey(const ValueKey<String>('review-reassign-confirm')),
    );
    await tester.pumpAndSettle();

    expect(repository.decisionCalls, hasLength(1));
    expect(
      repository.decisionCalls.single.note,
      'Take two on the flaky test',
    );
    expect(repository.decisionCalls.single.decision, DecisionEnum.reassign);
  });

  testWidgets('conflict errors surface a catalog-mapped friendly message',
      (WidgetTester tester) async {
    repository.nextDecisionError =
        apiError(CodeEnum.TASK_STATE_CONFLICT, statusCode: 409);
    await pumpReview(tester);
    await openReassign(tester);
    await tester.tap(
      find.byKey(const ValueKey<String>('review-reassign-confirm')),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey<String>('review-notice')),
      findsOneWidget,
    );
    expect(
      find.textContaining('no longer awaiting review'),
      findsOneWidget,
      reason: 'TASK_STATE_CONFLICT maps to catalog-only friendly copy',
    );
    expect(
      find.byKey(const ValueKey<String>('review-outcome-reassign')),
      findsNothing,
      reason: 'a rejected reassign records no outcome on the sheet',
    );
  });
}
