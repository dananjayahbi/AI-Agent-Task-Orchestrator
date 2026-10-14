import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/routes.dart';
import 'package:orchestrator_mobile/features/review/review_screen.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import 'review_test_support.dart';

/// The dialog's note field and send button (shared finders).
Finder get noteField =>
    find.byKey(const ValueKey<String>('review-request-note-field'));
Finder get sendButton =>
    find.byKey(const ValueKey<String>('review-request-submit'));

/// MT-5.8-05 widget battery: request changes with dictated note —
/// dictate → editable text → send, permission/capability degradation to
/// typed input, the T16 required-note guard, the success outcome, and
/// the discard confirmation (Section 14.2 voice-note rules).
void main() {
  late FakeReviewRepository repository;
  late FakeDictationService dictation;

  setUp(() {
    repository = FakeReviewRepository(
      decisionResponse: makeReviewResponse(
        decision: DecisionEnum.requestChanges,
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
    dictation = FakeDictationService();
  });

  Future<void> pumpReview(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: reviewOverrides(
          repository: repository,
          dictation: dictation,
        ),
        child: MaterialApp(
          onGenerateRoute: onGenerateRoute,
          onUnknownRoute: onUnknownRoute,
          home: ReviewScreen(taskId: reviewTaskId),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Future<void> openRequestChanges(WidgetTester tester) async {
    await tester.tap(
      find.byKey(const ValueKey<String>('review-action-request-changes')),
    );
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('review-request-note-field')),
      findsOneWidget,
    );
  }

  testWidgets('dictate → editable transcript → send (text only, no audio)',
      (WidgetTester tester) async {
    dictation.transcriptOnStart = 'Fix the failing test';
    await pumpReview(tester);
    await openRequestChanges(tester);

    // The on-device promise is stated right where dictation is offered.
    expect(
      find.byKey(const ValueKey<String>('review-request-dictation-hint')),
      findsOneWidget,
    );
    expect(
      find.textContaining('audio is never uploaded'),
      findsOneWidget,
    );

    // Empty note: T16 guard — submit disabled (whitespace counts empty).
    expect(
      tester.widget<FilledButton>(sendButton).onPressed,
      isNull,
    );
    await tester.enterText(noteField, '   ');
    await tester.pump();
    expect(tester.widget<FilledButton>(sendButton).onPressed, isNull,
        reason: 'whitespace-only counts as empty (Section 8.2 guard)');

    // Dictation fills the editable field. The dictating indicator is a
    // live spinner — pump frames, never pumpAndSettle, while it runs.
    await tester.tap(
      find.byKey(const ValueKey<String>('review-request-dictate')),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(dictation.startCalls, 1);
    expect(
      tester.widget<TextField>(noteField).controller!.text,
      'Fix the failing test',
    );
    expect(
      find.byKey(const ValueKey<String>('review-request-stop-dictating')),
      findsOneWidget,
      reason: 'the session is live and stoppable',
    );

    // Stop keeps the transcript; the field becomes editable again.
    await tester.tap(
      find.byKey(const ValueKey<String>('review-request-stop-dictating')),
    );
    await tester.pumpAndSettle();
    expect(dictation.stopCalls, 1);
    expect(
      find.byKey(const ValueKey<String>('review-request-dictate')),
      findsOneWidget,
    );
    expect(tester.widget<TextField>(noteField).controller!.text,
        'Fix the failing test');

    // The user edits before sending (Section 14.2).
    await tester.enterText(noteField, 'Fix the failing test please');
    await tester.pump();
    expect(tester.widget<FilledButton>(sendButton).onPressed, isNotNull);

    await tester.tap(sendButton);
    await tester.pumpAndSettle();

    expect(repository.decisionCalls, hasLength(1));
    final ReviewDecisionRequest request = repository.decisionCalls.single;
    expect(request.decision, DecisionEnum.requestChanges);
    expect(request.note, 'Fix the failing test please');
    expect(request.version, 7);
    expect(request.resolutionId, isNull,
        reason: 'only approve binds a resolution id');

    // T16 outcome on the sheet: back to pending, decision recorded.
    expect(find.byType(ReviewScreen), findsOneWidget);
    expect(
      find.byKey(const ValueKey<String>('review-outcome-request_changes')),
      findsOneWidget,
    );
    expect(
      find.textContaining('request_changes recorded — task is now pending'),
      findsOneWidget,
    );
  });

  testWidgets(
      'permission denial degrades to typed input with a clear '
      'message (no dead end)', (WidgetTester tester) async {
    dictation.failWithPermission = true;
    await pumpReview(tester);
    await openRequestChanges(tester);

    await tester.tap(
      find.byKey(const ValueKey<String>('review-request-dictate')),
    );
    await tester.pumpAndSettle();
    expect(
      find.byKey(
        const ValueKey<String>('review-request-dictation-unavailable'),
      ),
      findsOneWidget,
    );
    expect(
      find.textContaining('type your note instead'),
      findsOneWidget,
    );

    // Typed input still works end to end.
    await tester.enterText(noteField, 'Typed after denial');
    await tester.pump();
    expect(tester.widget<FilledButton>(sendButton).onPressed, isNotNull);
    await tester.tap(sendButton);
    await tester.pumpAndSettle();
    expect(repository.decisionCalls, hasLength(1));
    expect(repository.decisionCalls.single.note, 'Typed after denial');
  });

  testWidgets('missing capability surfaces as dictation unavailable',
      (WidgetTester tester) async {
    dictation.failWithCapability = true;
    await pumpReview(tester);
    await openRequestChanges(tester);
    await tester.tap(
      find.byKey(const ValueKey<String>('review-request-dictate')),
    );
    await tester.pumpAndSettle();
    expect(
      find.textContaining('Dictation unavailable on this device'),
      findsOneWidget,
    );
    // The dialog stays usable — no crash, no dead end.
    expect(noteField, findsOneWidget);
    expect(tester.widget<FilledButton>(sendButton).onPressed, isNull);
  });

  testWidgets('dismissing with uncommitted text confirms first',
      (WidgetTester tester) async {
    await pumpReview(tester);
    await openRequestChanges(tester);
    await tester.enterText(noteField, 'half-written note');
    await tester.pump();

    // Barrier tap = a dismiss attempt (PopScope interception).
    await tester.tapAt(const Offset(4, 4));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('review-request-discard-keep')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-request-discard-confirm')),
      findsOneWidget,
    );

    // Keep editing: the note dialog survives with its text.
    await tester.tap(
      find.byKey(const ValueKey<String>('review-request-discard-keep')),
    );
    await tester.pumpAndSettle();
    expect(noteField, findsOneWidget);
    expect(
      tester.widget<TextField>(noteField).controller!.text,
      'half-written note',
    );

    // Discard: the dialog closes, nothing was sent.
    await tester.tapAt(const Offset(4, 4));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey<String>('review-request-discard-confirm')),
    );
    await tester.pumpAndSettle();
    expect(noteField, findsNothing);
    expect(repository.decisionCalls, isEmpty);
  });

  testWidgets('cancel with an empty note just closes (no confirmation)',
      (WidgetTester tester) async {
    await pumpReview(tester);
    await openRequestChanges(tester);
    await tester.tap(
      find.byKey(const ValueKey<String>('review-request-cancel')),
    );
    await tester.pumpAndSettle();
    expect(noteField, findsNothing);
    expect(
      find.byKey(const ValueKey<String>('review-request-discard-keep')),
      findsNothing,
    );
    expect(repository.decisionCalls, isEmpty);
  });
}
