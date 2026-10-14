import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/features/review/diff_parser.dart';
import 'package:orchestrator_mobile/features/review/diff_view.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import 'review_test_support.dart';

/// One unified-diff file section: accurate hunk counts so the parser's
/// body-consumption ends exactly at the section boundary (the same
/// discipline the web fixture patches use).
String fileSection(String path, List<String> bodyLines) {
  final int count = bodyLines.length;
  final StringBuffer buffer = StringBuffer()
    ..writeln('diff --git a/$path b/$path')
    ..writeln('index 1111111..2222222 100644')
    ..writeln('--- a/$path')
    ..writeln('+++ b/$path')
    ..writeln('@@ -1,$count +1,$count @@');
  for (final String line in bodyLines) {
    buffer.writeln(line);
  }
  return buffer.toString();
}

List<String> contextLines(String tag, int count) =>
    List<String>.generate(count, (int i) => ' $tag$i');

/// MT-5.8-03 widget battery: the lazy per-file diff renderer — laziness,
/// the Section 9.7 marker, per-file caps, highlighting fallback,
/// horizontal-scroll containment, and the empty/opaque states.
void main() {
  late FakeReviewRepository repository;

  setUp(() {
    repository = FakeReviewRepository()
      ..resolutions[reviewTaskId] = <Resolution>[makeReviewResolution()];
  });

  Future<void> pumpDiff(
    WidgetTester tester, {
    required Resolution resolution,
    int lineLimit = diffPerFileLineLimit,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: reviewOverrides(repository: repository),
        child: MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: DiffRegionView(
                resolution: resolution,
                lineLimit: lineLimit,
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets(
      'stats-only payloads show the Section 9.7 marker with the '
      'backend stats and file list', (WidgetTester tester) async {
    repository.patches['res-1'] = makePatch(
      tooLarge: true,
      marker: 'diff too large',
    );
    await pumpDiff(tester, resolution: makeReviewResolution());

    expect(
      find.byKey(const ValueKey<String>('review-diff-marker')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-diff-marker-phrase')),
      findsOneWidget,
    );
    expect(find.text('diff too large'), findsOneWidget);
    // Authoritative stats from diff_summary / changed_files — never
    // recomputed from a patch body (Section 9.7).
    expect(
      find.byKey(const ValueKey<String>('review-diff-marker-stats')),
      findsOneWidget,
    );
    expect(find.text('2 files · +42 −7'), findsOneWidget);
    expect(find.text('src/a.dart'), findsOneWidget);
    expect(find.text('src/b.dart'), findsOneWidget);
  });

  testWidgets('multi-file patch builds only the visible file (lazy per file)',
      (WidgetTester tester) async {
    repository.patches['res-1'] = makePatch(
      patchBody: <String>[
        fileSection('src/one.dart', contextLines('one', 40)),
        fileSection('src/two.dart', contextLines('two', 40)),
        fileSection('src/three.dart', contextLines('three', 40)),
      ].join(),
    );
    await pumpDiff(tester,
        resolution: makeReviewResolution(
          changedFiles: <String>[
            'src/one.dart',
            'src/two.dart',
            'src/three.dart'
          ],
        ));

    expect(
      find.byKey(const ValueKey<String>('review-diff-file-src/one.dart')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-diff-file-src/two.dart')),
      findsNothing,
      reason: 'file 2 sits beyond the fixed viewport — never pre-built '
          '(Section 14.2 lazy per file; zero cache extent)',
    );
    expect(
      find.byKey(const ValueKey<String>('review-diff-file-src/three.dart')),
      findsNothing,
    );

    // File navigation: "next file" jumps the scroll and updates the label.
    expect(
      find.byKey(const ValueKey<String>('review-diff-file-position')),
      findsOneWidget,
    );
    expect(find.text('File 1 of 3'), findsOneWidget);
    await tester.tap(
      find.byKey(const ValueKey<String>('review-diff-next-file')),
    );
    await tester.pumpAndSettle();
    expect(find.text('File 2 of 3'), findsOneWidget);
  });

  testWidgets('per-file line cap collapses the remainder behind Show more',
      (WidgetTester tester) async {
    repository.patches['res-1'] = makePatch(
      patchBody: fileSection('src/big.dart', contextLines('big', 50)),
    );
    await pumpDiff(
      tester,
      resolution: makeReviewResolution(changedFiles: <String>['src/big.dart']),
      lineLimit: 10,
    );

    // Cap 10 = the hunk header line + nine body lines.
    expect(find.textContaining('big8'), findsOneWidget);
    expect(find.textContaining('big9'), findsNothing,
        reason: 'line 9+ is behind the cap (RISK-13 discipline)');
    final Finder more = find.byKey(
      const ValueKey<String>('review-diff-show-more-src/big.dart'),
    );
    expect(more, findsOneWidget);
    expect(find.text('Show more (41 lines hidden)'), findsOneWidget);

    await tester.tap(more);
    await tester.pumpAndSettle();
    expect(find.textContaining('big18'), findsOneWidget,
        reason: 'the next chunk renders after Show more');
  });

  testWidgets('a pathological 5,000-line file stays capped and fast',
      (WidgetTester tester) async {
    final String body = contextLines('x', 5000).join('\n');
    final String patch = fileSection('src/huge.dart', <String>[
      for (final String line in body.split('\n')) line,
    ]);
    repository.patches['res-1'] = makePatch(patchBody: patch);

    final Stopwatch clock = Stopwatch()..start();
    await pumpDiff(
      tester,
      resolution: makeReviewResolution(changedFiles: <String>['src/huge.dart']),
    );
    clock.stop();

    expect(
      find.byKey(const ValueKey<String>('review-diff-file-src/huge.dart')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('review-diff-show-more-src/huge.dart')),
      findsOneWidget,
      reason: 'the default 400-line cap holds on a huge file',
    );
    expect(
      clock.elapsedMilliseconds,
      lessThan(4000),
      reason: 'Section 19 WP-4.7 performance bar applied to mobile',
    );
  });

  testWidgets('monospace lines scroll horizontally inside the region',
      (WidgetTester tester) async {
    final String longLine = '+${'averylongtoken' * 120}';
    repository.patches['res-1'] = makePatch(
      patchBody:
          fileSection('src/wide.dart', <String>[' $longLine'.trimRight()]),
    );
    await pumpDiff(
      tester,
      resolution: makeReviewResolution(changedFiles: <String>['src/wide.dart']),
    );

    expect(
      find.descendant(
        of: find
            .byKey(const ValueKey<String>('review-diff-file-src/wide.dart')),
        matching: find.byWidgetPredicate(
          (Widget widget) =>
              widget is SingleChildScrollView &&
              widget.scrollDirection == Axis.horizontal,
        ),
      ),
      findsOneWidget,
      reason: 'per-file horizontal scroll only — no page-level scroll',
    );
    // No exception was thrown for the overflowing line (soft wrap off).
    expect(tester.takeException(), isNull);
  });

  testWidgets('syntax highlighting applies per extension with plain fallback',
      (WidgetTester tester) async {
    // Pure-function contract first: keywords map by extension, plain
    // fallback for unknown ones.
    expect(keywordsForExtension('lib/a.dart'), contains('class'));
    expect(keywordsForExtension('lib/a.xyz'), isEmpty);
    final List<(String, bool)> spans =
        highlightLine('class Foo', keywordsForExtension('lib/a.dart'));
    expect(spans.first, ('class', true));

    // Widget-level: a .dart line highlights the keyword (bolder style),
    // an unknown extension renders one plain span.
    repository.patches['res-1'] = makePatch(
      patchBody: <String>[
        fileSection('lib/high.dart', <String>['+class High {}']),
        fileSection('lib/plain.xyz', <String>['+class Plain {}']),
      ].join(),
    );
    await pumpDiff(
      tester,
      resolution: makeReviewResolution(
        changedFiles: <String>['lib/high.dart', 'lib/plain.xyz'],
      ),
      lineLimit: 200,
    );

    final Text dartLine = _richTextContaining(tester, 'class High');
    final TextSpan dartRoot = dartLine.textSpan! as TextSpan;
    final List<InlineSpan> dartSpans =
        (dartRoot.children ?? <InlineSpan>[]).cast<InlineSpan>();
    expect(dartSpans.length, greaterThan(1),
        reason: 'the dart keyword is split out into its own span');
    final TextSpan keyword = dartSpans.first as TextSpan;
    expect(keyword.text, 'class');
    expect(keyword.style?.fontWeight, FontWeight.w600);

    final Text plainLine = _richTextContaining(tester, 'class Plain');
    final TextSpan plainRoot = plainLine.textSpan! as TextSpan;
    final List<InlineSpan> plainSpans =
        (plainRoot.children ?? <InlineSpan>[]).cast<InlineSpan>();
    expect(plainSpans.length, 1,
        reason: 'unknown extension → single plain span (fallback)');
    expect((plainSpans.first as TextSpan).style?.fontWeight,
        isNot(FontWeight.w600));
  });

  testWidgets('an empty patch is a legitimate empty diff, not an error',
      (WidgetTester tester) async {
    repository.patches['res-1'] = makePatch(patchBody: '');
    await pumpDiff(
      tester,
      resolution: makeReviewResolution(changedFiles: const <String>[]),
    );
    expect(
      find.byKey(const ValueKey<String>('review-diff-empty')),
      findsOneWidget,
    );
    expect(find.text('No file changes in this patch.'), findsOneWidget);
  });

  testWidgets('unparseable prose renders as-is, never as a file table',
      (WidgetTester tester) async {
    repository.patches['res-1'] = makePatch(
      patchBody: 'something the parser does not recognize\n',
    );
    await pumpDiff(
      tester,
      resolution: makeReviewResolution(changedFiles: const <String>[]),
    );
    expect(
      find.byKey(const ValueKey<String>('review-diff-opaque')),
      findsOneWidget,
    );
    expect(
      find.text('Unrecognized patch text (shown as-is)'),
      findsOneWidget,
    );
  });

  test('interpretPatchPayload follows the server, never byte guesses', () {
    final PatchPayloadResult tooLarge = interpretPatchPayload(
      diffTooLarge: true,
      patch: null,
      marker: null,
    );
    expect(tooLarge, isA<NoBodyPatchResult>());
    expect((tooLarge as NoBodyPatchResult).marker, 'diff too large');

    // An empty body is a legitimate empty diff — distinct from no-body.
    final PatchPayloadResult empty = interpretPatchPayload(
      diffTooLarge: false,
      patch: '',
      marker: null,
    );
    expect(empty, isA<ParsedPatchResult>());
    expect((empty as ParsedPatchResult).patch.files, isEmpty);
  });
}

/// Finds the first [Text.rich] in the tree whose text contains [needle].
Text _richTextContaining(WidgetTester tester, String needle) {
  return tester.widget<Text>(
    find.byWidgetPredicate(
      (Widget widget) =>
          widget is Text &&
          widget.textSpan != null &&
          widget.textSpan!.toPlainText().contains(needle),
    ),
  );
}
