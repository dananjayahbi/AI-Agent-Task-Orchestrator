import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/routes.dart';
import 'package:orchestrator_mobile/features/review/review_screen.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import 'review_test_support.dart';

/// MT-5.8-02 widget battery: rule results and evidence — every R1–R9
/// outcome from `policy_rule_results` with the failing rule's Section
/// 8.4 reason, the engine version, the Section 10.5 evidence shape,
/// the missing-report degradation, and unknown-key tolerance.
void main() {
  late FakeReviewRepository repository;

  setUp(() {
    repository = FakeReviewRepository()
      ..tasks[reviewTaskId] = makeReviewTask()
      ..resolutions[reviewTaskId] = <Resolution>[makeReviewResolution()]
      ..patches['res-1'] = makePatch(patchBody: '');
  });

  Future<void> pumpReview(WidgetTester tester) async {
    // A tall surface so the whole sheet is in the initial viewport —
    // this battery tests content, not scrolling (the diff region owns
    // its own laziness test).
    tester.view.physicalSize = const Size(1080, 2600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
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

  testWidgets(
      'failing R2/R5 render with their Section 8.4 reasons and '
      'every rule keeps a row (Section 9.4)', (WidgetTester tester) async {
    repository.reports[reviewTaskId] = <AuditReport>[
      makeAuditReport(
        ruleResults: ruleResultsJson(failing: <String>['R2', 'R5']),
      ),
    ];
    await pumpReview(tester);

    // Both failures render, canonical + friendly, no truncation.
    expect(
      find.byKey(const ValueKey<String>('review-rule-R2')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-rule-R5')),
      findsOneWidget,
    );
    expect(
      find.textContaining('Review reason: scope_violation'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Review reason: sensitive_config_changed'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Changes outside the task scope'),
      findsOneWidget,
      reason: 'friendly label for the failing rule reason',
    );

    // Failures first; the passing block collapses behind a disclosure —
    // and the passing rules are all still there when expanded.
    final Finder r2 = find.byKey(const ValueKey<String>('review-rule-R2'));
    final Finder passingDisclosure = find.byKey(
      const ValueKey<String>('review-rules-passing'),
    );
    expect(
      tester.getTopLeft(r2).dy,
      lessThan(tester.getTopLeft(passingDisclosure).dy),
      reason: 'failing rules render before the collapsed passing block',
    );
    expect(
      find.byKey(const ValueKey<String>('review-rule-R9')),
      findsNothing,
      reason: 'passing rules start collapsed',
    );
    await tester.tap(passingDisclosure);
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('review-rule-R9')),
      findsOneWidget,
    );
    expect(r2, findsOneWidget);

    // Engine version visible for traceability (Section 9.4).
    expect(
      find.byKey(const ValueKey<String>('review-rules-engine-version')),
      findsOneWidget,
    );
    expect(find.textContaining('engine 1.0.0'), findsOneWidget);
  });

  testWidgets('a fully-passing report renders the whole nine-row table',
      (WidgetTester tester) async {
    repository.reports[reviewTaskId] = <AuditReport>[
      makeAuditReport(
        ruleResults: ruleResultsJson(failing: const <String>[]),
        policyDecision: PolicyDecisionEnum.approve,
        proposedVerdict: ProposedVerdictEnum.pass,
      ),
    ];
    await pumpReview(tester);

    for (final String rule in <String>[
      'R1',
      'R2',
      'R3',
      'R4',
      'R5',
      'R6',
      'R7',
      'R8',
      'R9',
    ]) {
      expect(
        find.byKey(ValueKey<String>('review-rule-$rule')),
        findsOneWidget,
        reason: '$rule must render — Section 9.4 persists all nine',
      );
    }
    expect(
      find.byKey(const ValueKey<String>('review-rules-passing')),
      findsNothing,
      reason: 'nothing to collapse on a full-pass table',
    );
    expect(find.textContaining('Policy decision: approve'), findsOneWidget);
  });

  testWidgets(
      'evidence renders commands with exit codes, lint, criteria, '
      'confidence and verdict (Sections 7.2 / 10.5)',
      (WidgetTester tester) async {
    repository.reports[reviewTaskId] = <AuditReport>[
      makeAuditReport(ruleResults: ruleResultsJson(failing: <String>['R1'])),
    ];
    await pumpReview(tester);

    expect(
      find.byKey(const ValueKey<String>('review-evidence-confidence')),
      findsOneWidget,
    );
    expect(find.textContaining('Confidence 2 of 5'), findsOneWidget);
    expect(find.textContaining('Proposed verdict: fail'), findsOneWidget);
    expect(
      find.textContaining('Policy decision: escalate'),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-evidence-lint')),
      findsOneWidget,
    );
    expect(find.text('Lint clean'), findsOneWidget);

    // The failing command with its exit code (Section 10.5 shape) —
    // label and command text are two separate rows.
    expect(
      find.text('flutter test'),
      findsNWidgets(2),
    );
    expect(
      find.byKey(const ValueKey<String>('review-command-exit-flutter test')),
      findsOneWidget,
    );
    expect(find.text('exit 1'), findsOneWidget);
    expect(find.text('12 failed'), findsOneWidget);

    // Acceptance-criteria results per criterion.
    expect(find.text('covers the bug'), findsOneWidget);

    // Auditor notes are their own Section 14.1 region.
    expect(
      find.byKey(const ValueKey<String>('review-auditor-notes')),
      findsOneWidget,
    );
  });

  testWidgets('missing report degrades without errors or fake pass tables',
      (WidgetTester tester) async {
    repository.reports[reviewTaskId] = <AuditReport>[
      makeAuditReport(
        id: 'report-pre-engine',
        ruleResults: null,
        policyDecision: null,
        engineVersion: null,
      ),
    ];
    await pumpReview(tester);

    expect(
      find.byKey(const ValueKey<String>('review-rules-missing')),
      findsOneWidget,
      reason: 'null policy_rule_results reads as "not recorded"',
    );
    expect(
      find.byKey(const ValueKey<String>('review-rule-R1')),
      findsNothing,
      reason: 'never a fabricated pass table (Sections 8.5 / 20.3)',
    );
    // The rest of the sheet still renders.
    expect(
      find.byKey(const ValueKey<String>('review-execution-summary')),
      findsOneWidget,
    );
  });

  testWidgets('unknown evidence keys render collapsed, never guessed',
      (WidgetTester tester) async {
    repository.reports[reviewTaskId] = <AuditReport>[
      makeAuditReport(
        ruleResults: ruleResultsJson(),
        evidence: <String, Object?>{
          'commands': <Object?>[],
          'mystery_blob': <String, Object?>{'depth': 3},
          'wall_time_ms': 4211,
        },
      ),
    ];
    await pumpReview(tester);

    final Finder disclosure = find.byKey(
      const ValueKey<String>('review-evidence-unknown-keys'),
    );
    expect(disclosure, findsOneWidget);
    expect(
      find.textContaining('Additional evidence keys (2)'),
      findsOneWidget,
    );

    // Collapsed: the values are not on screen yet.
    expect(find.textContaining('mystery_blob'), findsNothing);
    expect(find.textContaining('depth'), findsNothing);

    await tester.tap(disclosure);
    await tester.pumpAndSettle();
    expect(find.textContaining('mystery_blob: '), findsOneWidget);
    expect(find.textContaining('wall_time_ms: 4211'), findsOneWidget);
  });
}
