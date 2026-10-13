import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/offline/json_cache.dart';
import 'package:orchestrator_mobile/core/realtime/orchestrator_event.dart';
import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/core/realtime/sse_connection_status.dart';
import 'package:orchestrator_mobile/core/realtime/sse_lifecycle_binder.dart';
import 'package:orchestrator_mobile/core/security/auth_gate.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/board/board_event_patcher.dart';
import 'package:orchestrator_mobile/features/board/board_providers.dart';
import 'package:orchestrator_mobile/features/board/board_repository.dart';
import 'package:orchestrator_mobile/features/board/current_project.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';
import '../security/security_test_support.dart';
import 'board_test_support.dart';

/// MT-5.6-04 battery: foreground live updates over the shared MT-5.5-05
/// SSE client (extend, don't fork) — events patch the board without a
/// refresh, backgrounding suspends the stream, the subscription follows
/// the MT-5.6-02 selection, staleness/catalog guards hold, and a dead
/// stream falls back to polling with an honest liveness state.
void main() {
  group('foreground events patch the board (Section 19 acceptance)', () {
    late FakeBoardRepository board;
    late FakeSseTransport transport;
    late InMemoryLastEventIdStore store;
    late SseClient client;
    late ProviderContainer container;
    late bool disposed;

    setUp(() {
      board = FakeBoardRepository()
        ..tasksByProject['P1'] = <Task>[
          makeTask(
            id: 'T1',
            projectId: 'P1',
            state: StateEnum.draft,
            title: 'Live task',
          ),
          makeTask(
            id: 'T2',
            projectId: 'P1',
            state: StateEnum.inProgress,
            version: 2,
            workerAgentId: 'agent-1',
          ),
        ];
      transport = FakeSseTransport();
      store = InMemoryLastEventIdStore();
      client = buildTestSseClient(transport: transport, store: store);
      container = ProviderContainer(
        overrides: <Override>[
          boardRepositoryProvider.overrideWithValue(board),
          jsonCacheProvider.overrideWithValue(InMemoryJsonCache()),
          sseClientProvider.overrideWithValue(client),
        ],
      );
      disposed = false;
      addTearDown(() async {
        if (!disposed) {
          disposed = true;
          container.dispose();
          await client.dispose();
        }
      });
    });

    Future<void> loadProject(String projectId) async {
      container.read(boardProvider); // create the notifier
      await pumpEventQueue();
      container.read(currentProjectProvider.notifier).select(projectId);
      await pumpEventQueue();
      expect(board.listCallsFor(projectId), 1);
    }

    Future<void> cleanup() async {
      if (!disposed) {
        disposed = true;
        container.dispose();
        await client.dispose();
      }
    }

    test(
        'a task.transitioned event moves the card between pages while '
        'foregrounded — no user refresh (FR-MOB-02 real-time Kanban)',
        () async {
      transport.queueStream();
      await loadProject('P1');
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);

      transport.emitTo(
        0,
        envelopeJson(
          id: 1,
          projectId: 'P1',
          taskId: 'T1',
          type: 'task.transitioned',
          data: <String, dynamic>{'to_state': 'in_progress', 'task_version': 2},
        ),
      );
      await waitFor(
        () =>
            container
                .read(boardProvider)
                .tasks
                .firstWhere((Task t) => t.id == 'T1')
                .state ==
            StateEnum.inProgress,
        reason: 'the event must patch the idle board state live',
      );
      final Task patched = container
          .read(boardProvider)
          .tasks
          .firstWhere((Task t) => t.id == 'T1');
      expect(patched.version, 2);
      expect(board.listCallsFor('P1'), 1,
          reason: 'a pure patch never triggers a board-list refetch');
      await cleanup();
    });

    test('stale task_version is ignored — newer local data never regresses',
        () async {
      transport.queueStream();
      await loadProject('P1');
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);

      // T2 is at version 2; an event claiming version 1 must be dropped.
      transport.emitTo(
        0,
        envelopeJson(
          id: 1,
          projectId: 'P1',
          taskId: 'T2',
          type: 'task.transitioned',
          data: <String, dynamic>{'to_state': 'draft', 'task_version': 1},
        ),
      );
      await pumpEventQueue();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      final Task t2 = container
          .read(boardProvider)
          .tasks
          .firstWhere((Task t) => t.id == 'T2');
      expect(t2.state, StateEnum.inProgress,
          reason: 'the stale event must not regress the card');
      expect(t2.version, 2);
      await cleanup();
    });

    test(
        'unknown and non-catalog event types are ignored without breaking '
        'the stream (Section 20.4 item 6)', () async {
      transport.queueStream();
      await loadProject('P1');
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);

      // Catalog type outside board scope (no task_id → not a board patch).
      transport.emitTo(
        0,
        envelopeJson(id: 1, projectId: 'P1', type: 'system.alert'),
      );
      // Not in the closed catalog at all.
      transport.emitTo(
        0,
        envelopeJson(
          id: 2,
          projectId: 'P1',
          taskId: 'T1',
          type: 'task.exploded',
        ),
      );
      await pumpEventQueue();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(container.read(boardProvider).status, BoardStatus.ready);
      expect(
        container.read(boardProvider).tasks.first.state,
        StateEnum.draft,
      );

      // The stream survives and still applies a known event afterwards.
      transport.emitTo(
        0,
        envelopeJson(
          id: 3,
          projectId: 'P1',
          taskId: 'T1',
          type: 'task.transitioned',
          data: <String, dynamic>{'to_state': 'pending', 'task_version': 1},
        ),
      );
      await waitFor(
        () =>
            container.read(boardProvider).tasks.first.state ==
            StateEnum.pending,
      );
      await cleanup();
    });

    test(
        'the subscription carries the current project filter and follows '
        'selection changes — reconnect keeps Last-Event-ID (Section 9.6)',
        () async {
      transport
        ..queueStream()
        ..queueStream();
      container.read(boardProvider);
      await pumpEventQueue();
      container.read(currentProjectProvider.notifier).select('P1');
      await pumpEventQueue();

      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);
      expect(transport.openedQuery.first['project'], 'P1',
          reason: 'the stream opens with the selection filter');

      transport.emitTo(
        0,
        envelopeJson(
          id: 1,
          projectId: 'P1',
          taskId: 'T1',
          type: 'task.transitioned',
          data: <String, dynamic>{'to_state': 'pending', 'task_version': 1},
        ),
      );
      await waitFor(() =>
          container.read(boardProvider.notifier).appliedEventIds.contains(1));

      // Selection change (MT-5.6-02) re-filters the live subscription.
      container.read(currentProjectProvider.notifier).select('P2');
      await pumpEventQueue();
      await waitFor(() => transport.openCount == 2,
          reason: 'a filter switch reconnects the shared client');
      expect(transport.openedQuery[1]['project'], 'P2');
      expect(transport.openedHeaders[1]['Last-Event-ID'], '1',
          reason: 'reconnect replays the gap — no event lost in the switch');
      expect(board.listCallsFor('P2'), 1,
          reason: 'board refetch follows the same selection');
      await cleanup();
    });

    test(
        'stream loss falls back to polling: full refetch, history carries '
        'the project filter, honest status (Section 14.2, RISK-05)', () async {
      final FakeEventHistorySource history = FakeEventHistorySource();
      await client.dispose();
      client = buildTestSseClient(
        transport: transport,
        history: history,
        store: store,
        maxStreamFailures: 2,
      );
      container = ProviderContainer(
        overrides: <Override>[
          boardRepositoryProvider.overrideWithValue(board),
          jsonCacheProvider.overrideWithValue(InMemoryJsonCache()),
          sseClientProvider.overrideWithValue(client),
        ],
      );

      transport.queueStream();
      await loadProject('P1');
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);
      final int baseline = board.listCallsFor('P1');

      // The stream dies and every reconnect attempt fails.
      transport
        ..closeAt(0)
        ..queueError(StateError('tunnel down'))
        ..queueError(StateError('tunnel down'));

      await waitFor(() => client.status.value == SseConnectionStatus.polling,
          reason: 'repeated stream failure must enter the polling fallback');
      expect(client.status.value, isNot(SseConnectionStatus.connected),
          reason: 'never claim live while polling');

      // The board reconciles with a full refetch on entering fallback.
      await waitFor(() => board.listCallsFor('P1') > baseline);
      // History polling carries the same project filter.
      await waitFor(() => history.calls.isNotEmpty);
      expect(history.calls.first['project'], 'P1');
      await cleanup();
    });
  });

  group('foreground/background lifecycle (Section 14.2)', () {
    testWidgets(
        'the stream runs only while foregrounded and unlocked: pausing the '
        'app suspends the subscription, resuming restarts it',
        (WidgetTester tester) async {
      final FakeSseTransport transport = FakeSseTransport()
        ..queueStream()
        ..queueStream();
      final SseClient client = buildTestSseClient(transport: transport);
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(
          deviceTokenStorageKey, 'tok'); // pragma: allowlist secret
      bool disposed = false;
      Future<void> cleanup() async {
        if (!disposed) {
          disposed = true;
          await client.dispose();
        }
      }

      addTearDown(cleanup);

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            secureTokenStoreProvider.overrideWithValue(store),
            biometricAuthProvider
                .overrideWithValue(FakeBiometricAuthenticator()),
            sseClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: SseLifecycleBinder(child: Text('shell')),
          ),
        ),
      );
      // Gate unlocks to a stored credential → foreground → start.
      final ProviderContainer scope = ProviderScope.containerOf(
        tester.element(find.text('shell')),
        listen: false,
      );
      await scope.read(authGateProvider.notifier).unlock();
      await tester.pump();
      await tester.pump();

      expect(transport.openCount, 1,
          reason: 'foreground + unlocked connects the shared client');
      expect(client.isRunning, isTrue);

      // Backgrounded: the subscription must not stay open.
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      await tester.pump();
      expect(client.isRunning, isFalse,
          reason: 'backgrounding suspends the stream (no battery drain)');

      // Foreground again: reconnects (replay handled by the client).
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump();
      await tester.pump();
      expect(client.isRunning, isTrue);
      expect(transport.openCount, 2);

      await tester.pumpWidget(const SizedBox());
      await cleanup();
    });
  });

  group('patcher guards (pure functions)', () {
    final Task draft = makeTask(
      id: 'T1',
      projectId: 'P1',
      state: StateEnum.draft,
      version: 3,
    );

    OrchestratorEvent event({
      required int id,
      String type = 'task.transitioned',
      String projectId = 'P1',
      String taskId = 'T1',
      Map<String, dynamic>? data,
    }) =>
        OrchestratorEvent.tryParse(<String, dynamic>{
          'id': id,
          'type': type,
          'project_id': projectId,
          'task_id': taskId,
          'occurred_at': '2026-10-11T12:45:02Z',
          'actor': <String, dynamic>{'type': 'agent', 'ref': 'a-1'},
          'data': data ?? <String, dynamic>{},
        })!;

    test(
        'pure patch applies state + version; duplicate application is '
        'idempotent (Section 9.6 no duplicates)', () {
      final OrchestratorEvent e = event(
        id: 1,
        data: <String, dynamic>{'to_state': 'pending', 'task_version': 4},
      );
      final BoardPatchResult first = applyEventToBoard(
        <Task>[draft],
        e,
        boardProjectId: 'P1',
      );
      expect(first.tasks.single.state, StateEnum.pending);
      expect(first.tasks.single.version, 4);
      expect(first.refetchTaskIds, isEmpty);

      final BoardPatchResult second = applyEventToBoard(
        first.tasks,
        e,
        boardProjectId: 'P1',
      );
      expect(second.tasks.single.state, StateEnum.pending);
      expect(second.tasks.single.version, 4,
          reason: 'applying the same event again changes nothing');
    });

    test('stale task_version is ignored — identical list returned', () {
      final List<Task> input = <Task>[draft];
      final BoardPatchResult result = applyEventToBoard(
        input,
        event(
          id: 9,
          data: <String, dynamic>{'to_state': 'completed', 'task_version': 2},
        ),
        boardProjectId: 'P1',
      );
      expect(identical(result.tasks, input), isTrue,
          reason: 'an event older than the cache changes nothing');
      expect(result.tasks.single.state, StateEnum.draft);
      expect(result.tasks.single.version, 3);
    });

    test('foreign-project events never land on this board', () {
      final List<Task> input = <Task>[draft];
      final BoardPatchResult result = applyEventToBoard(
        input,
        event(
          id: 5,
          projectId: 'OTHER',
          data: <String, dynamic>{'to_state': 'completed', 'task_version': 9},
        ),
        boardProjectId: 'P1',
      );
      expect(identical(result.tasks, input), isTrue);
      expect(result.tasks.single.state, StateEnum.draft);
    });

    test(
        'task.created schedules a targeted refetch and mergeRefetchedTask '
        'inserts the missed row (MT-5.6-05 reconciliation)', () {
      final BoardPatchResult result = applyEventToBoard(
        <Task>[draft],
        event(id: 7, type: 'task.created', taskId: 'NEW'),
        boardProjectId: 'P1',
      );
      expect(result.refetchTaskIds, <String>['NEW']);

      final Task fresh = makeTask(
        id: 'NEW',
        projectId: 'P1',
        state: StateEnum.pending,
        title: 'Missed while suspended',
      );
      final List<Task> merged = mergeRefetchedTask(
        result.tasks,
        fresh,
        boardProjectId: 'P1',
      );
      expect(merged.map((Task t) => t.id), <String>['T1', 'NEW']);
      expect(merged.last.title, 'Missed while suspended');

      // An older row never regresses a newer cached one.
      final Task older = fresh.rebuild((TaskBuilder b) => b.version = 0);
      expect(
        identical(
            mergeRefetchedTask(merged, older, boardProjectId: 'P1'), merged),
        isTrue,
      );
    });
  });
}
