import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/core/realtime/sse_connection_status.dart';
import 'package:orchestrator_mobile/features/task_detail/checkpoint_feed_providers.dart';
import 'package:orchestrator_mobile/features/task_detail/checkpoint_feed_view.dart';
import 'package:orchestrator_mobile/features/task_detail/task_detail_repository.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart'
    hide DashboardSummary, ProjectDashboardCard;

import '../realtime/realtime_test_support.dart';
import 'task_detail_test_support.dart';

/// MT-5.7-02 battery: the live checkpoint feed — foreground live append,
/// background/resume replay with exactly-once checkpoint ids
/// (Section 9.6 "no gaps, no duplicates"), history/event dedupe with the
/// documented reconciliation order, the Section 14.2 polling fallback
/// with its visible degraded indicator, and safe handling of unknown or
/// malformed events (Section 20.4 item 6).
void main() {
  late FakeTaskDetailRepository repository;
  late FakeSseTransport transport;
  late SseClient client;
  late ProviderContainer container;

  setUp(() {
    repository = FakeTaskDetailRepository()
      ..checkpointPages['T1'] = <CheckpointPage>[
        CheckpointPage(checkpoints: <Checkpoint>[
          makeCheckpoint(
            id: 'c-h1',
            message: 'From history',
            percent: 10,
            timestamp: DateTime.utc(2026, 10, 11, 12, 0),
          ),
        ]),
      ];
    transport = FakeSseTransport();
    client = buildDetailTestSseClient(transport: transport);
    container = ProviderContainer(
      overrides: taskDetailOverrides(
        repository: repository,
        sseClient: client,
      ),
    );
    addTearDown(() async {
      container.dispose();
      await client.dispose();
    });
  });

  CheckpointFeedState feed() => container.read(checkpointFeedProvider('T1'));

  CheckpointFeedNotifier feedNotifier() =>
      container.read(checkpointFeedProvider('T1').notifier);

  Future<void> loadFeed() async {
    // Hold a subscription: the family is autoDispose, and these plain
    // container tests would otherwise dispose it between reads.
    container.listen(checkpointFeedProvider('T1'), (_, __) {});
    await pumpEventQueue();
  }

  List<String> shownIds() =>
      feed().checkpoints.map((Checkpoint c) => c.id).toList();

  Map<String, dynamic> checkpointEvent({
    required int id,
    String checkpointId = 'c-live',
    String taskId = 'T1',
    int? percent = 50,
    String message = 'Live checkpoint',
    String kind = 'progress',
    String occurredAt = '2026-10-11T13:00:00Z',
    Map<String, dynamic>? data,
  }) =>
      envelopeJson(
        id: id,
        type: 'task.checkpoint',
        taskId: taskId,
        occurredAt: occurredAt,
        data: data ??
            <String, dynamic>{
              'checkpoint_id': checkpointId,
              'attempt_number': 1,
              'kind': kind,
              'percent': percent,
              'session_id': 'session-1',
              'message': message,
              'token_usage': <String, dynamic>{'prompt': 10},
            },
      );

  group('foreground live append (acceptance item 1)', () {
    test('task.checkpoint events append with percent, message and tokens',
        () async {
      await loadFeed();
      expect(shownIds(), <String>['c-h1']);

      transport.queueStream();
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);
      transport.emitTo(
        0,
        checkpointEvent(id: 1, checkpointId: 'c-live'),
      );
      await waitFor(() => feed().checkpoints.length == 2);

      final Checkpoint live =
          feed().checkpoints.firstWhere((Checkpoint c) => c.id == 'c-live');
      expect(live.message, 'Live checkpoint');
      expect(live.percent, 50);
      expect(live.kind, 'progress');
      expect(live.tokenUsage!.value, <String, dynamic>{'prompt': 10});
    });

    test('ordering is server-timestamp first, id tiebreak (P7)', () async {
      await loadFeed();
      transport.queueStream();
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);

      // Arrives out of order: an older live checkpoint after a newer one.
      transport.emitTo(
        0,
        checkpointEvent(
          id: 1,
          checkpointId: 'c-new',
          occurredAt: '2026-10-11T14:00:00Z',
        ),
      );
      transport.emitTo(
        0,
        checkpointEvent(
          id: 2,
          checkpointId: 'c-old',
          occurredAt: '2026-10-11T13:30:00Z',
        ),
      );
      await waitFor(() => feed().checkpoints.length == 3);

      expect(shownIds(), <String>['c-new', 'c-old', 'c-h1'],
          reason: 'server timestamps order the feed, never arrival order');
    });
  });

  group('background/resume replay (acceptance item 2; Section 9.6)', () {
    test('a drop + resume replays the gap and appends exactly once', () async {
      transport
        ..queueStream()
        ..queueStream();
      await loadFeed();
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);

      transport.emitTo(
        0,
        checkpointEvent(id: 1, checkpointId: 'c-live-1'),
      );
      await waitFor(() => feed().checkpoints.length == 2);
      expect(client.lastProcessedEventId, 1);

      // "Backgrounding": the server drops the socket.
      transport.closeAt(0);
      await waitFor(() => transport.openCount == 2);
      expect(transport.openedHeaders[1]['Last-Event-ID'], '1',
          reason: 'resume from the last event id (Section 14.2)');

      // Server replays the gap: overlap (id 1) + missed ids 2 and 3.
      transport.emitTo(
        1,
        checkpointEvent(id: 1, checkpointId: 'c-live-1'),
      );
      transport.emitTo(
        1,
        checkpointEvent(
            id: 2,
            checkpointId: 'c-live-2',
            occurredAt: '2026-10-11T13:05:00Z'),
      );
      transport.emitTo(
        1,
        checkpointEvent(
            id: 3,
            checkpointId: 'c-live-3',
            occurredAt: '2026-10-11T13:10:00Z'),
      );
      await waitFor(() => feed().checkpoints.length == 4);

      final List<String> ids = shownIds();
      expect(ids.toSet().length, ids.length,
          reason: 'no duplicate checkpoint rows after replay');
      expect(ids,
          containsAll(<String>['c-h1', 'c-live-1', 'c-live-2', 'c-live-3']));
    });
  });

  group('history/event dedupe (acceptance item 5; reconciliation order)', () {
    test(
        'events arriving during the initial fetch are buffered and '
        'deduped against the history rows', () async {
      // Park the history fetch, deliver the overlapping event, then
      // release — the classic Section 14.2 resume double-render case.
      final ScriptedGate gate = ScriptedGate();
      repository.checkpointGate = gate;
      final Future<void> load = loadFeed();

      transport.queueStream();
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);
      await waitFor(() => repository.checkpointCalls.isNotEmpty);
      // The live event overlaps a history row (same checkpoint id) and
      // adds one genuinely new checkpoint.
      transport.emitTo(
        0,
        checkpointEvent(
          id: 1,
          checkpointId: 'c-h1',
          message: 'From history',
          occurredAt: '2026-10-11T12:00:00Z',
        ),
      );
      transport.emitTo(
        0,
        checkpointEvent(id: 2, checkpointId: 'c-after'),
      );
      await pumpEventQueue();

      gate.release();
      await load;
      await waitFor(() => feed().checkpoints.length == 2);

      expect(shownIds(), <String>['c-after', 'c-h1'],
          reason: 'the replayed history overlap renders exactly once');
    });

    test('loadOlder appends the next cursor page without duplicating',
        () async {
      repository.checkpointPages['T1'] = <CheckpointPage>[
        const CheckpointPage(checkpoints: <Checkpoint>[], nextCursor: 'cur-1'),
        CheckpointPage(checkpoints: <Checkpoint>[
          makeCheckpoint(
            id: 'c-older',
            message: 'Older',
            timestamp: DateTime.utc(2026, 10, 11, 10, 0),
          ),
        ]),
      ];
      await loadFeed();
      expect(feed().olderCursor, 'cur-1');

      await feedNotifier().loadOlder();
      await pumpEventQueue();

      expect(shownIds(), <String>['c-older']);
      expect(feed().olderCursor, isNull,
          reason: 'the last page clears the cursor');
    });
  });

  group('polling fallback (acceptance item 3; Section 14.2)', () {
    test(
        'entering the client polling state starts checkpoint polling '
        'with a visible degraded indicator; SSE recovery stops it', () async {
      // Swap in a client with a minimal failure budget so the first
      // drop throws it into the documented polling fallback.
      container.dispose();
      await client.dispose();
      client = buildDetailTestSseClient(
        transport: transport,
        maxStreamFailures: 1,
        pollInterval: const Duration(milliseconds: 5),
      );
      container = ProviderContainer(
        overrides: taskDetailOverrides(
          repository: repository,
          sseClient: client,
        ),
      );

      await loadFeed();
      feedNotifier().pollInterval = const Duration(milliseconds: 5);

      // The stream cannot be maintained: two opens fail, then recovery.
      transport
        ..queueError(StateError('drop'))
        ..queueError(StateError('drop'))
        ..queueStream();
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.polling,
          timeout: const Duration(seconds: 3));

      // The feed polls the checkpoints endpoint and merges by id.
      repository.checkpointPages['T1'] = <CheckpointPage>[
        CheckpointPage(checkpoints: <Checkpoint>[
          makeCheckpoint(
            id: 'c-polled',
            message: 'Polled',
            timestamp: DateTime.utc(2026, 10, 11, 15, 0),
          ),
          makeCheckpoint(
            id: 'c-h1',
            message: 'From history',
            percent: 10,
            timestamp: DateTime.utc(2026, 10, 11, 12, 0),
          ),
        ]),
      ];
      await waitFor(() => shownIds().contains('c-polled'),
          timeout: const Duration(seconds: 3));
      expect(feed().isDegradedPolling, isTrue,
          reason: 'the degraded state is visible, never labeled live');
      expect(shownIds().toSet().length, shownIds().length,
          reason: 'polling merges never duplicate');

      // SSE recovers: the client reconnects and the fallback stops.
      await waitFor(() => client.status.value == SseConnectionStatus.connected,
          timeout: const Duration(seconds: 3));
      await waitFor(() => !feed().isDegradedPolling,
          timeout: const Duration(seconds: 3));
    });
  });

  group('catalog-only processing (acceptance item 6; Section 20.4.6)', () {
    test('non-checkpoint events are ignored outright', () async {
      await loadFeed();
      transport.queueStream();
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);

      transport.emitTo(
        0,
        envelopeJson(
          id: 1,
          type: 'task.transitioned',
          taskId: 'T1',
          data: <String, dynamic>{'to_state': 'pending'},
        ),
      );
      await client.pause();
      expect(feed().checkpoints.length, 1,
          reason: 'only task.checkpoint events touch the feed');
    });

    test('a malformed checkpoint event is skipped, not fatal', () async {
      await loadFeed();
      transport.queueStream();
      await client.start();
      await waitFor(() => client.status.value == SseConnectionStatus.connected);

      // Missing checkpoint_id — the documented required wire field.
      transport.emitTo(
        0,
        envelopeJson(
          id: 1,
          type: 'task.checkpoint',
          taskId: 'T1',
          data: <String, dynamic>{'message': 'no id'},
        ),
      );
      // The stream survives: a well-formed event still lands.
      transport.emitTo(
        0,
        checkpointEvent(id: 2, checkpointId: 'c-after-bad'),
      );
      await waitFor(() => feed().checkpoints.length == 2);
      expect(shownIds(), contains('c-after-bad'));
    });
  });

  group('widget states (Section 20.3)', () {
    Future<void> pumpFeed(
      WidgetTester tester, {
      CheckpointFeedState? primed,
    }) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: taskDetailOverrides(
            repository: repository,
            sseClient: client,
          ),
          child: MaterialApp(
            home: Scaffold(
              body: SizedBox(
                height: 400,
                child: CheckpointFeedView(taskId: 'T1'),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets(
        'renders rows with percent, kind and token usage; empty '
        'state when there are none', (WidgetTester tester) async {
      repository.checkpointPages['T1'] = <CheckpointPage>[
        CheckpointPage(checkpoints: <Checkpoint>[
          makeCheckpoint(
            id: 'c1',
            message: 'Working on it',
            percent: 60,
            tokenUsage: <String, dynamic>{'completion': 42, 'nested': 1},
          ),
          makeCheckpoint(id: 'c2', percent: null, message: ''),
        ]),
      ];
      await pumpFeed(tester);

      expect(find.byKey(const ValueKey<String>('checkpoint-row-c1')),
          findsOneWidget);
      expect(find.text('60%'), findsOneWidget);
      expect(find.text('completion: 42 · nested: 1'), findsOneWidget,
          reason: 'primitive token usage entries render as key: value');
      // Nullable percent is honest, never a fake 0.
      expect(find.text('Progress unknown'), findsOneWidget);
      expect(find.text('No message.'), findsOneWidget);
    });

    testWidgets('error state shows friendly copy and a working retry',
        (WidgetTester tester) async {
      repository
        ..checkpointPages['T1'] = <CheckpointPage>[
          const CheckpointPage(checkpoints: <Checkpoint>[]),
        ]
        ..nextCheckpointError =
            apiError(CodeEnum.SERVER_ERROR, statusCode: 500);
      await pumpFeed(tester);

      expect(
        find.byKey(const ValueKey<String>('checkpoint-feed-error')),
        findsOneWidget,
      );
      expect(find.text('scripted'), findsNothing,
          reason: 'the raw server message never reaches the UI');

      await tester.tap(
        find.byKey(const ValueKey<String>('checkpoint-feed-retry')),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey<String>('checkpoint-feed-empty')),
        findsOneWidget,
      );
    });

    testWidgets(
        'the degraded polling banner and honest label render in the '
        'polling state (Section 14.2)', (WidgetTester tester) async {
      // Deterministic widget-state test: the notifier is scripted to the
      // degraded state — no client, no timers (the plain test above
      // already covers the status→polling wiring end to end).
      repository.checkpointPages['T1'] = <CheckpointPage>[
        const CheckpointPage(checkpoints: <Checkpoint>[]),
      ];
      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            ...taskDetailOverrides(
              repository: repository,
              sseClient: client,
            ),
            checkpointFeedProvider.overrideWith(
              () => ScriptedCheckpointFeedNotifier(
                CheckpointFeedState.ready(
                  checkpoints: <Checkpoint>[
                    makeCheckpoint(id: 'c1', message: 'Live row'),
                  ],
                  isDegradedPolling: true,
                ),
              ),
            ),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: SizedBox(
                height: 400,
                child: CheckpointFeedView(taskId: 'T1'),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey<String>('checkpoint-degraded-banner')),
        findsOneWidget,
      );
      expect(find.text('Live row'), findsOneWidget,
          reason: 'the feed keeps showing rows while degraded');
      expect(
        find.byKey(const ValueKey<String>('checkpoint-liveness')),
        findsOneWidget,
      );
    });
  });
}
