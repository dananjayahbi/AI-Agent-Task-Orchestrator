import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/offline/json_cache.dart';
import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/core/realtime/sse_connection_status.dart';
import 'package:orchestrator_mobile/features/board/board_providers.dart';
import 'package:orchestrator_mobile/features/board/board_repository.dart';
import 'package:orchestrator_mobile/features/board/board_states.dart';
import 'package:orchestrator_mobile/features/board/current_project.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';
import 'board_test_support.dart';

/// MT-5.6-05 battery: resume replay from the last event id after
/// suspension (Section 14.2 / Section 9.6 "no gaps, no duplicates") over
/// the shared MT-5.5-05 client — exact applied counts, persisted resume
/// id, first-launch live-only path, replay-failure refetch fallback, and
/// the reconciliation of tasks missed while suspended.
void main() {
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
          title: 'Replay task',
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

  Future<void> loadBoard() async {
    container.read(boardProvider);
    await pumpEventQueue();
    container.read(currentProjectProvider.notifier).select('P1');
    await pumpEventQueue();
    expect(board.listCallsFor('P1'), 1);
  }

  List<int> applied() => container.read(boardProvider.notifier).appliedEventIds;

  Task onBoard(String id) =>
      container.read(boardProvider).tasks.firstWhere((Task t) => t.id == id);

  test(
      'after a drop, the reconnect replays the gap from the last event id '
      'and the board applies exactly the missed range — no duplicates '
      '(Section 9.6)', () async {
    transport
      ..queueStream()
      ..queueStream();
    await loadBoard();
    await client.start();
    await waitFor(() => client.status.value == SseConnectionStatus.connected);

    // Live tail: ids 1 and 2 move the card forward.
    transport.emitTo(
      0,
      envelopeJson(
        id: 1,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{'to_state': 'pending', 'task_version': 2},
      ),
    );
    transport.emitTo(
      0,
      envelopeJson(
        id: 2,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{
          'to_state': 'in_progress',
          'task_version': 3,
        },
      ),
    );
    await waitFor(() => applied().length == 2);
    expect(applied(), <int>[1, 2]);
    expect(store.value, 2, reason: 'resume id persisted as events process');

    // Suspension moment: the server drops the socket.
    transport.closeAt(0);
    await waitFor(() => transport.openCount == 2,
        reason: 'the client reconnects after suspension');
    expect(transport.openedHeaders[1]['Last-Event-ID'], '2',
        reason: 'resume from the last event id (Section 14.2)');

    // Server replays: overlap (id 2 again) + missed ids 3 and 4.
    transport.emitTo(
      1,
      envelopeJson(
        id: 2,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{'to_state': 'completed', 'task_version': 9},
      ),
    );
    transport.emitTo(
      1,
      envelopeJson(
        id: 3,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{
          'to_state': 'to_be_audited',
          'task_version': 4,
        },
      ),
    );
    transport.emitTo(
      1,
      envelopeJson(
        id: 4,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{
          'to_state': 'in_human_review',
          'task_version': 5,
        },
      ),
    );
    await waitFor(() => applied().length == 4,
        reason: 'the replayed backlog must be applied');

    expect(applied(), <int>[1, 2, 3, 4],
        reason: 'exactly the known missed range — no gaps, no duplicates');
    expect(onBoard('T1').state, StateEnum.inHumanReview,
        reason: 'replay ended on server truth');
    expect(onBoard('T1').version, 5);
    expect(store.value, 4);
  });

  test(
      'first launch without a stored id takes the live-only path — no '
      'fabricated resume id (MT-5.6-05 acceptance)', () async {
    transport.queueStream();
    await loadBoard();
    expect(store.value, isNull);

    await client.start();
    await waitFor(() => client.status.value == SseConnectionStatus.connected);
    expect(
      transport.openedHeaders.first.containsKey('Last-Event-ID'),
      isFalse,
      reason: 'a fresh install must not invent an id',
    );

    transport.emitTo(
      0,
      envelopeJson(
        id: 5,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{'to_state': 'pending', 'task_version': 2},
      ),
    );
    await waitFor(() => applied().length == 1);
    expect(applied(), <int>[5]);
    expect(store.value, 5);
  });

  test(
      'the stored last id survives suspension: a fresh client process '
      'attaches it on the next connect', () async {
    transport.queueStream();
    await loadBoard();
    await client.start();
    await waitFor(() => client.status.value == SseConnectionStatus.connected);
    transport.emitTo(
      0,
      envelopeJson(
        id: 1,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{'to_state': 'pending', 'task_version': 2},
      ),
    );
    await waitFor(() => store.value == 1);

    // "Process death": the client instance goes away; storage remains.
    container.dispose();
    await client.dispose();
    disposed = true;

    final FakeSseTransport freshTransport = FakeSseTransport()..queueStream();
    final SseClient freshClient = buildTestSseClient(
      transport: freshTransport,
      store: store,
    );
    final ProviderContainer freshContainer = ProviderContainer(
      overrides: <Override>[
        boardRepositoryProvider.overrideWithValue(board),
        jsonCacheProvider.overrideWithValue(InMemoryJsonCache()),
        sseClientProvider.overrideWithValue(freshClient),
      ],
    );
    addTearDown(() async {
      freshContainer.dispose();
      await freshClient.dispose();
    });

    freshContainer.read(boardProvider);
    await pumpEventQueue();
    freshContainer.read(currentProjectProvider.notifier).select('P1');
    await pumpEventQueue();

    await freshClient.start();
    await waitFor(
        () => freshClient.status.value == SseConnectionStatus.connected);
    expect(freshTransport.openedHeaders.first['Last-Event-ID'], '1',
        reason: 'the persisted marker drives resume across restarts');
  });

  test(
      'a rejected replay falls back to a full refetch and then live — the '
      'board is reconciled, never presented stale (Section 14.2, RISK-05)',
      () async {
    await client.dispose();
    client = buildTestSseClient(
      transport: transport,
      store: store,
      maxStreamFailures: 1,
    );
    container = ProviderContainer(
      overrides: <Override>[
        boardRepositoryProvider.overrideWithValue(board),
        jsonCacheProvider.overrideWithValue(InMemoryJsonCache()),
        sseClientProvider.overrideWithValue(client),
      ],
    );

    transport
      ..queueStream()
      ..queueError(StateError('replay window exceeded'));
    await loadBoard();
    await client.start();
    await waitFor(() => client.status.value == SseConnectionStatus.connected);
    transport.emitTo(
      0,
      envelopeJson(
        id: 1,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{'to_state': 'pending', 'task_version': 2},
      ),
    );
    await waitFor(() => applied().length == 1);
    final int baseline = board.listCallsFor('P1');

    // Server truth meanwhile advanced (the row on the server is the
    // patched one) — the refetch below must land on exactly this.
    board.tasksByProject['P1'] = <Task>[
      makeTask(
        id: 'T1',
        projectId: 'P1',
        state: StateEnum.pending,
        version: 2,
        title: 'Replay task',
      ),
    ];

    // Suspension + resume: the server refuses the stale id → the client
    // degrades to polling (history catch-up), and the board refetches.
    transport.closeAt(0);
    await waitFor(() => client.status.value == SseConnectionStatus.polling);
    await waitFor(() => board.listCallsFor('P1') > baseline,
        reason: 'replay failure must trigger a full board refetch');

    // The stream comes back → live again.
    transport.queueStream();
    await waitFor(() => client.status.value == SseConnectionStatus.connected,
        reason: 'the client must recover to live after the fallback');
    expect(onBoard('T1').state, StateEnum.pending);
  });

  test(
      'a task missed entirely while suspended appears after replay through '
      'the same guarded patch path (MT-5.6-05 reconciliation)', () async {
    board.singleTasks['T2'] = makeTask(
      id: 'T2',
      projectId: 'P1',
      state: StateEnum.pending,
      title: 'Created while suspended',
    );
    transport
      ..queueStream()
      ..queueStream();
    await loadBoard();
    await client.start();
    await waitFor(() => client.status.value == SseConnectionStatus.connected);
    transport.emitTo(
      0,
      envelopeJson(
        id: 1,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{'to_state': 'pending', 'task_version': 2},
      ),
    );
    await waitFor(() => applied().length == 1);

    transport.closeAt(0);
    await waitFor(() => transport.openCount == 2);
    expect(transport.openedHeaders[1]['Last-Event-ID'], '1');

    // Replayed backlog: the unknown task was created while suspended.
    transport.emitTo(
      1,
      envelopeJson(
        id: 2,
        projectId: 'P1',
        taskId: 'T2',
        type: 'task.created',
      ),
    );
    await waitFor(
        () => container.read(boardProvider).tasks.any((Task t) => t.id == 'T2'),
        reason: 'the missed task must appear after replay');
    expect(
      board.singleTaskCalls,
      contains('T2'),
      reason: 'a targeted single-task refetch, never a board-list refetch',
    );
    expect(
      groupTasksByState(container.read(boardProvider).tasks)[StateEnum.pending]!
          .map((Task t) => t.id),
      contains('T2'),
      reason: 'the row lands on its canonical page (G-01 grouping)',
    );
    expect(applied(), <int>[1, 2]);
  });

  test(
      'applied ids are strictly monotonic — out-of-order delivery is '
      'dropped, never double-applied (Section 9.6)', () async {
    transport.queueStream();
    await loadBoard();
    await client.start();
    await waitFor(() => client.status.value == SseConnectionStatus.connected);

    transport.emitTo(
      0,
      envelopeJson(
        id: 1,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{'to_state': 'pending', 'task_version': 2},
      ),
    );
    transport.emitTo(
      0,
      envelopeJson(
        id: 3,
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{
          'to_state': 'in_progress',
          'task_version': 4,
        },
      ),
    );
    transport.emitTo(
      0,
      envelopeJson(
        id: 2, // late, out of order — must be dropped by the id guards
        projectId: 'P1',
        taskId: 'T1',
        data: <String, dynamic>{'to_state': 'draft', 'task_version': 3},
      ),
    );
    await waitFor(() => applied().length == 2);
    await Future<void>.delayed(const Duration(milliseconds: 30));

    expect(applied(), <int>[1, 3],
        reason: 'the id-2 event must never be applied after id 3');
    expect(onBoard('T1').state, StateEnum.inProgress);
    expect(onBoard('T1').version, 4);
  });
}
