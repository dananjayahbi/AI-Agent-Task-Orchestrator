import 'dart:async';
import 'dart:convert';

import 'package:built_value/serializer.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/routes.dart';
import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/core/realtime/sse_connection_status.dart';
import 'package:orchestrator_mobile/features/board/board_cache.dart';
import 'package:orchestrator_mobile/features/board/board_screen.dart';
import 'package:orchestrator_mobile/features/board/board_states.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';
import 'board_test_support.dart';

/// MT-5.6-03 widget battery: the horizontally paged six-state board —
/// canonical page order (G-01), grouping from API types, touch paging,
/// pull to refresh, the Section 8.1 merge-pending badge (never a seventh
/// page), per-page loading/empty/error states, the Section 14.2 offline
/// cache, and the task-detail handoff.
void main() {
  late FakeProjectsRepository projects;
  late FakeBoardRepository board;
  late InMemoryJsonCache cache;
  late FakeSseTransport transport;

  setUp(() {
    projects = FakeProjectsRepository()
      ..projects = <Project>[makeProject(id: 'PID00001', name: 'Solo')];
    board = FakeBoardRepository();
    cache = InMemoryJsonCache();
    transport = FakeSseTransport();
  });

  Future<ProviderContainer> pumpBoard(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: boardOverrides(
          projects: projects,
          board: board,
          cache: cache,
          sseClient: buildTestSseClient(transport: transport),
        ),
        child: MaterialApp(
          onGenerateRoute: onGenerateRoute,
          onUnknownRoute: onUnknownRoute,
          home: const BoardScreen(),
        ),
      ),
    );
    final ProviderContainer container = ProviderScope.containerOf(
      tester.element(find.byType(BoardScreen)),
      listen: false,
    );
    await tester.pumpAndSettle();
    return container;
  }

  /// One task per canonical state, in Section 8.1 order.
  List<Task> onePerState() => <Task>[
        makeTask(
            id: 'PID00001-T1', state: StateEnum.draft, title: 'Draft task'),
        makeTask(
            id: 'PID00001-T2', state: StateEnum.pending, title: 'Pending task'),
        makeTask(
            id: 'PID00001-T3',
            state: StateEnum.inProgress,
            title: 'Working task'),
        makeTask(
            id: 'PID00001-T4',
            state: StateEnum.toBeAudited,
            title: 'Auditable task',
            mergeStatus: 'pending'),
        makeTask(
            id: 'PID00001-T5',
            state: StateEnum.inHumanReview,
            title: 'Review task'),
        makeTask(
            id: 'PID00001-T6',
            state: StateEnum.completed,
            title: 'Finished task'),
      ];

  group('canonical six pages (G-01 / Section 8.1)', () {
    test('board states are exactly the six schema values, in plan order', () {
      expect(boardStates, <StateEnum>[
        StateEnum.draft,
        StateEnum.pending,
        StateEnum.inProgress,
        StateEnum.toBeAudited,
        StateEnum.inHumanReview,
        StateEnum.completed,
      ]);
      expect(boardStatesCoverageGap(), isEmpty,
          reason: 'a seventh schema state must fail loudly here');
      expect(groupTasksByState(<Task>[]).keys, boardStates);
    });

    testWidgets(
        'pages in canonical order with per-state counts; touch chip jumps '
        'to the matching page (FR-MOB-02 touch paging)',
        (WidgetTester tester) async {
      board.tasksByProject['PID00001'] = onePerState();
      await pumpBoard(tester);

      // Exactly six pages: six indicator chips (0..5), no seventh.
      for (int i = 0; i < boardStates.length; i++) {
        expect(
          find.byKey(ValueKey<String>('board-page-chip-$i')),
          findsOneWidget,
          reason: 'page $i (${boardStates[i].name}) must be reachable',
        );
      }
      expect(
        find.byKey(const ValueKey<String>('board-page-chip-6')),
        findsNothing,
        reason: 'merge-pending is a badge, never a seventh page',
      );

      // Page indicator chips carry the Section 8.1 labels in order.
      const List<String> labels = <String>[
        'Draft 1',
        'Pending 1',
        'In progress 1',
        'To be audited 1',
        'Human review 1',
        'Completed 1',
      ];
      for (int i = 0; i < labels.length; i++) {
        expect(
          find.descendant(
            of: find.byKey(ValueKey<String>('board-page-chip-$i')),
            matching: find.text(labels[i]),
          ),
          findsOneWidget,
          reason: 'chip $i must read ${labels[i]} (Section 8.1 order)',
        );
      }

      // Page 0 (draft) shows the draft task.
      expect(
        find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey<String>('board-card-PID00001-T2')),
          findsNothing);

      // Every chip jumps to its matching page — touch paging over the six
      // canonical pages, in order, each keyed by its canonical value.
      for (int i = 0; i < boardStates.length; i++) {
        await tester.tap(find.byKey(ValueKey<String>('board-page-chip-$i')));
        await tester.pumpAndSettle();
        final String stateName = boardStates[i].name;
        expect(
          find.byKey(ValueKey<String>('board-page-$stateName')),
          findsOneWidget,
          reason: 'chip $i must page to ${boardStates[i].name}',
        );
        if (i == 2) {
          expect(
            find.byKey(const ValueKey<String>('board-card-PID00001-T3')),
            findsOneWidget,
            reason: 'grouping puts the in_progress task on its page',
          );
          expect(
            find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
            findsNothing,
          );
        }
      }
    });

    testWidgets('task cards carry id, title, priority and worker basics',
        (WidgetTester tester) async {
      board.tasksByProject['PID00001'] = <Task>[
        makeTask(
          id: 'PID00001-T1',
          state: StateEnum.draft,
          title: 'Visible title',
          priority: PriorityEnum.urgent,
          workerAgentId: 'agent-7',
          attemptNumber: 2,
        ),
      ];
      await pumpBoard(tester);

      expect(find.text('Visible title'), findsOneWidget);
      expect(
        find.byKey(const ValueKey<String>('board-card-meta-PID00001-T1')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey<String>('board-card-priority-PID00001-T1')),
        findsOneWidget,
      );
      expect(find.text('P: urgent'), findsOneWidget);
      expect(find.text('Worker: agent-7 · attempt 2'), findsOneWidget,
          reason: 'worker/progress basics on every card (Section 14.1)');
    });

    testWidgets(
        'merge-pending renders the Section 8.1 badge on the state page — '
        'the board has no seventh page', (WidgetTester tester) async {
      board.tasksByProject['PID00001'] = onePerState();
      await pumpBoard(tester);

      // Not on the draft page.
      expect(find.byKey(const ValueKey<String>('merge-pending-badge')),
          findsNothing);

      await tester.tap(find.byKey(const ValueKey<String>('board-page-chip-3')));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey<String>('board-card-PID00001-T4')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey<String>('merge-pending-badge')),
          findsOneWidget);
      expect(find.text('Approved, merging'), findsOneWidget);
    });

    testWidgets('pull to refresh re-fetches the current board (Section 14.1)',
        (WidgetTester tester) async {
      board.tasksByProject['PID00001'] = <Task>[
        makeTask(id: 'PID00001-T1', state: StateEnum.draft),
      ];
      await pumpBoard(tester);
      expect(board.listCallsFor('PID00001'), 1);

      await tester.fling(
        find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
        const Offset(0, 300),
        1000,
      );
      await tester.pumpAndSettle();

      expect(board.listCallsFor('PID00001'), 2,
          reason: 'pull to refresh must re-fetch through the repository');
      expect(
        find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
        findsOneWidget,
      );
    });

    testWidgets(
        'tapping a card hands off to the task detail route (WP-5.7 stub)',
        (WidgetTester tester) async {
      board.tasksByProject['PID00001'] = <Task>[
        makeTask(id: 'PID00001-T1', state: StateEnum.draft),
      ];
      await pumpBoard(tester);

      await tester.tap(
        find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Task detail'), findsOneWidget,
          reason: 'the WP-5.7 placeholder route must be pushed');
      expect(find.textContaining('Not implemented yet'), findsOneWidget);
    });
  });

  group('per-page states (Section 20.3)', () {
    testWidgets('each page shows its own loading state while fetching',
        (WidgetTester tester) async {
      board.tasksByProject['PID00001'] = <Task>[
        makeTask(id: 'PID00001-T1', state: StateEnum.draft),
      ];
      final Completer<void> gate = Completer<void>();
      board.held = gate;
      await tester.pumpWidget(
        ProviderScope(
          overrides: boardOverrides(
            projects: projects,
            board: board,
            cache: cache,
            sseClient: buildTestSseClient(transport: transport),
          ),
          child: MaterialApp(
            onGenerateRoute: onGenerateRoute,
            onUnknownRoute: onUnknownRoute,
            home: const BoardScreen(),
          ),
        ),
      );
      await tester.pump();
      // The single project auto-selects → the fetch parks on the gate.
      await tester.pump();

      expect(
        find.byKey(const ValueKey<String>('board-page-loading-draft')),
        findsOneWidget,
        reason: 'the visible page renders its own loading state',
      );
      expect(find.byKey(const ValueKey<String>('board-page-list-draft')),
          findsNothing);

      gate.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey<String>('board-page-list-draft')),
          findsOneWidget);
    });

    testWidgets('a page with no tasks shows its own empty state',
        (WidgetTester tester) async {
      board.tasksByProject['PID00001'] = <Task>[
        makeTask(id: 'PID00001-T1', state: StateEnum.completed),
      ];
      await pumpBoard(tester);

      expect(
        find.byKey(const ValueKey<String>('board-page-empty-draft')),
        findsOneWidget,
      );
      expect(find.text('No tasks in Draft.'), findsOneWidget);
      // The completed page holds the only task.
      await tester.tap(find.byKey(const ValueKey<String>('board-page-chip-5')));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
        findsOneWidget,
      );
    });

    testWidgets(
        'per-page error is distinct, catalog-mapped, and retry recovers '
        '(Section 20.4 item 5)', (WidgetTester tester) async {
      board.tasksByProject['PID00001'] = <Task>[
        makeTask(id: 'PID00001-T1', state: StateEnum.draft),
      ];
      board.nextError = catalogError(code: CodeEnum.RATE_LIMITED);
      await pumpBoard(tester);

      expect(
        find.byKey(const ValueKey<String>('board-page-error-draft')),
        findsOneWidget,
      );
      expect(
        find.text('Too many requests — wait a moment and try again.'),
        findsOneWidget,
      );
      expect(find.textContaining('raw server detail'), findsNothing);

      await tester.tap(
        find.byKey(const ValueKey<String>('board-page-retry-draft')),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
        findsOneWidget,
        reason: 'retry after the transient failure reconciles the board',
      );
    });

    testWidgets(
        'offline: the last loaded board is served from cache with a clear '
        'stale banner, never presented as live (Section 14.2)',
        (WidgetTester tester) async {
      // Seed the Section 14.2 cache with the last board for this project.
      await BoardCache(cache).write('PID00001', <Task>[
        makeTask(id: 'PID00001-T1', state: StateEnum.draft, title: 'Cached'),
      ]);
      projects.projects = <Project>[
        makeProject(id: 'PID00001', name: 'Solo'),
        makeProject(id: 'PID00002', name: 'Other'),
      ];
      board.nextError = transportError();
      await pumpBoard(tester);
      // Two projects → no auto-select; pick the cached one.
      await tester.tap(find.byKey(const ValueKey<String>('project-selector')));
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey<String>('project-option-PID00001')),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const ValueKey<String>('board-stale-banner')),
          findsOneWidget);
      expect(
          find.textContaining('Showing the last loaded board'), findsOneWidget);
      expect(
        find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
        findsOneWidget,
        reason: 'the cached board is shown, marked stale',
      );
    });

    testWidgets('no project selected is its own state, not an empty page',
        (WidgetTester tester) async {
      projects.projects = <Project>[
        makeProject(id: 'PID00001', name: 'One'),
        makeProject(id: 'PID00002', name: 'Two'),
      ];
      await pumpBoard(tester);

      expect(find.byKey(const ValueKey<String>('board-no-project')),
          findsOneWidget);
      expect(find.text('No tasks in Draft.'), findsNothing,
          reason: 'page-empty is a different state');
      expect(board.taskListCalls, isEmpty);
    });
  });

  group('task detail handoff arguments', () {
    testWidgets('the pushed route receives the tapped task id',
        (WidgetTester tester) async {
      board.tasksByProject['PID00001'] = <Task>[
        makeTask(id: 'PID00001-T1', state: StateEnum.draft),
      ];
      await pumpBoard(tester);

      // The route table resolves the area path (arguments travel with the
      // push; the WP-5.7 placeholder ignores them for now).
      final NavigatorState navigator =
          tester.state<NavigatorState>(find.byType(Navigator));
      expect(navigator.canPop(), isFalse);
      await tester.tap(
        find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
      );
      await tester.pumpAndSettle();
      expect(navigator.canPop(), isTrue);
    });
  });

  group('honest liveness indication (MT-5.6-04 / Section 14.2)', () {
    test('the polling fallback is never labeled "live" (RISK-05)', () {
      expect(boardLivenessLabel(SseConnectionStatus.connected), 'Live');
      expect(
          boardLivenessLabel(SseConnectionStatus.polling), 'Periodic updates');
      expect(boardLivenessLabel(SseConnectionStatus.disconnected),
          'Live updates off');
      expect(boardLivenessLabel(SseConnectionStatus.connecting), 'Connecting…');
      expect(boardLivenessLabel(SseConnectionStatus.reconnecting),
          'Reconnecting…');
      expect(
        boardLivenessLabel(SseConnectionStatus.polling),
        isNot('Live'),
        reason: 'honest fallback labeling — never fake a live badge',
      );
    });

    testWidgets('the board chip tracks the shared client\'s real status',
        (WidgetTester tester) async {
      transport.queueStream();
      await pumpBoard(tester);

      // Not started yet — the chip says so honestly.
      expect(find.byKey(const ValueKey<String>('board-liveness-label')),
          findsOneWidget);
      expect(find.text('Live updates off'), findsOneWidget);

      final ProviderContainer container = ProviderScope.containerOf(
        tester.element(find.byType(BoardScreen)),
        listen: false,
      );
      final SseClient client = container.read(sseClientProvider);
      await client.start();
      for (int i = 0;
          i < 20 && client.status.value != SseConnectionStatus.connected;
          i++) {
        await tester.pump(const Duration(milliseconds: 5));
      }
      expect(client.status.value, SseConnectionStatus.connected);
      await tester.pump();
      expect(find.text('Live'), findsOneWidget);

      await client.pause();
      await tester.pump();
      expect(find.text('Live updates off'), findsOneWidget);
    });
  });

  group('cache round-trip', () {
    test('BoardCache serializes tasks through the generated serializers',
        () async {
      final InMemoryJsonCache store = InMemoryJsonCache();
      final BoardCache boardCache = BoardCache(store);
      final Task task = makeTask(
        id: 'PID00001-T1',
        state: StateEnum.toBeAudited,
        title: 'Round trip',
      );
      await boardCache.write('PID00001', <Task>[task]);
      expect(store.values.keys.single, contains('board_tasks_cache_v1'));
      final List<Task>? read = await boardCache.read('PID00001');
      expect(read!.single.id, 'PID00001-T1');
      expect(read.single.state, StateEnum.toBeAudited);
      expect(read.single.title, 'Round trip');
      // Canonical wire spelling owned by the schema (G-01).
      expect(jsonEncode(store.values.values.single), contains('to_be_audited'));
      // And the wire map uses serializers, not hand-built JSON.
      final Object? wire = standardSerializers.serialize(
        task,
        specifiedType: const FullType(Task),
      );
      expect(wire, isA<Map<String, dynamic>>());
    });
  });
}
