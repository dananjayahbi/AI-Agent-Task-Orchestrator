import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:orchestrator_mobile/core/realtime/event_history_source.dart';
import 'package:orchestrator_mobile/core/realtime/orchestrator_event.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/core/realtime/sse_connection_status.dart';

import 'realtime_test_support.dart';

/// MT-5.5-05 acceptance battery with a fake transport: envelope parsing,
/// exactly-once replay, pause/resume, backoff schedule, polling fallback.
void main() {
  SseClient buildClient({
    required FakeSseTransport transport,
    required FakeEventHistorySource history,
    required InMemoryLastEventIdStore store,
    int? maxStreamFailures,
    Duration pollInterval = const Duration(milliseconds: 5),
    Duration heartbeatTimeout = const Duration(seconds: 30),
    List<String>? warnings,
  }) {
    return SseClient(
      transport: transport,
      history: history,
      idStore: store,
      backoff: fastBackoff(
        maxStreamFailures: maxStreamFailures ?? 3,
        pollInterval: pollInterval,
      ),
      heartbeatTimeout: heartbeatTimeout,
      onWarning:
          warnings == null ? (_) {} : (String message) => warnings.add(message),
    );
  }

  test('live frames emit typed events; malformed is skipped with a warning',
      () async {
    final FakeSseTransport transport = FakeSseTransport()..queueStream();
    final List<String> warnings = <String>[];
    final SseClient client = buildClient(
      transport: transport,
      history: FakeEventHistorySource(),
      store: InMemoryLastEventIdStore(),
      warnings: warnings,
    );
    final List<OrchestratorEvent> received = <OrchestratorEvent>[];
    client.events.listen(received.add);

    await client.start();
    await waitFor(() => client.status.value == SseConnectionStatus.connected);

    transport.emitTo(0, envelopeJson(id: 1));
    transport.emitRawTo(0, 'data: {malformed\n\n');
    transport.emitTo(0, envelopeJson(id: 2));
    await waitFor(() => received.length == 2);

    expect(received.map((OrchestratorEvent e) => e.id), <int>[1, 2]);
    expect(received.first.type, 'task.transitioned');
    expect(warnings, contains(contains('malformed')));

    await client.dispose();
  });

  test(
      'reconnect sends Last-Event-ID and replayed events are processed exactly once',
      () async {
    final InMemoryLastEventIdStore store = InMemoryLastEventIdStore();
    final FakeSseTransport transport = FakeSseTransport()
      ..queueStream()
      ..queueStream();
    final SseClient client = buildClient(
      transport: transport,
      history: FakeEventHistorySource(),
      store: store,
    );
    final List<int> receivedIds = <int>[];
    client.events.listen((OrchestratorEvent e) => receivedIds.add(e.id));

    await client.start();
    await waitFor(() => client.status.value == SseConnectionStatus.connected);
    transport.emitTo(0, envelopeJson(id: 1));
    transport.emitTo(0, envelopeJson(id: 2));
    await waitFor(() => receivedIds.length == 2);

    // Server drops the connection — the client reconnects with its resume id.
    transport.closeAt(0);
    await waitFor(() => transport.openCount == 2,
        reason: 'client must reconnect after a drop');
    expect(transport.openedHeaders[1]['Last-Event-ID'], '2');

    // Server replays the gap: id 2 again (overlap) plus the missed id 3.
    transport.emitTo(1, envelopeJson(id: 2));
    transport.emitTo(1, envelopeJson(id: 3));
    await waitFor(() => receivedIds.length == 3);

    expect(receivedIds, <int>[1, 2, 3],
        reason: 'the replayed duplicate must be skipped exactly once');
    expect(store.value, 3, reason: 'last processed id persisted');

    await client.dispose();
  });

  test('a starting client loads the persisted resume id from storage',
      () async {
    final InMemoryLastEventIdStore store = InMemoryLastEventIdStore(12);
    final FakeSseTransport transport = FakeSseTransport()..queueStream();
    final SseClient client = buildClient(
      transport: transport,
      history: FakeEventHistorySource(),
      store: store,
    );

    await client.start();
    await waitFor(() => transport.openCount == 1);
    expect(transport.openedHeaders.single['Last-Event-ID'], '12');

    await client.dispose();
  });

  test('heartbeat comments never move the resume position', () async {
    final InMemoryLastEventIdStore store = InMemoryLastEventIdStore();
    final FakeSseTransport transport = FakeSseTransport()..queueStream();
    final SseClient client = buildClient(
      transport: transport,
      history: FakeEventHistorySource(),
      store: store,
    );
    final List<int> receivedIds = <int>[];
    client.events.listen((OrchestratorEvent e) => receivedIds.add(e.id));

    await client.start();
    await waitFor(() => transport.openCount == 1);
    transport.emitHeartbeatTo(0);
    transport.emitHeartbeatTo(0);
    transport.emitTo(0, envelopeJson(id: 5));
    transport.emitHeartbeatTo(0);
    await waitFor(() => receivedIds.length == 1);

    expect(receivedIds, <int>[5]);
    expect(client.lastProcessedEventId, 5);
    expect(store.value, 5);

    await client.dispose();
  });

  test('pause disconnects; resume reconnects with replay from the same id',
      () async {
    final InMemoryLastEventIdStore store = InMemoryLastEventIdStore();
    final FakeSseTransport transport = FakeSseTransport()
      ..queueStream()
      ..queueStream();
    final SseClient client = buildClient(
      transport: transport,
      history: FakeEventHistorySource(),
      store: store,
    );
    final List<int> receivedIds = <int>[];
    client.events.listen((OrchestratorEvent e) => receivedIds.add(e.id));

    await client.start();
    await waitFor(() => transport.openCount == 1);
    transport.emitTo(0, envelopeJson(id: 1));
    await waitFor(() => receivedIds.length == 1);

    // App pause: the connection must close and the loop must stop.
    final Future<void> paused = client.pause();
    await paused;
    expect(client.status.value, SseConnectionStatus.disconnected);
    expect(transport.controllerAt(0).isClosed, isTrue);

    // App resume: fresh connection carrying the resume id.
    await client.resume();
    await waitFor(() => transport.openCount == 2);
    expect(transport.openedHeaders[1]['Last-Event-ID'], '1');
    transport.emitTo(1, envelopeJson(id: 2));
    await waitFor(() => receivedIds.length == 2);
    expect(receivedIds, <int>[1, 2]);

    await client.dispose();
  });

  test('backoff schedule is exponential, capped, and jitter-bounded', () {
    const SseBackoffConfig config = SseBackoffConfig(
      initial: Duration(seconds: 1),
      max: Duration(seconds: 8),
      factor: 2,
      jitter: 0.2,
    );
    // Un-jittered: 1s, 2s, 4s, then cap.
    expect(
      SseBackoffConfig.unjitteredDelay(1, config),
      const Duration(seconds: 1),
    );
    expect(
      SseBackoffConfig.unjitteredDelay(2, config),
      const Duration(seconds: 2),
    );
    expect(
      SseBackoffConfig.unjitteredDelay(3, config),
      const Duration(seconds: 4),
    );
    expect(
      SseBackoffConfig.unjitteredDelay(4, config),
      const Duration(seconds: 8),
    );
    expect(
      SseBackoffConfig.unjitteredDelay(10, config),
      const Duration(seconds: 8),
      reason: 'the delay is capped (bounded backoff, NFR-04)',
    );
    // Jitter stays within ±20%.
    for (int attempt = 1; attempt <= 5; attempt++) {
      final Duration base = SseBackoffConfig.unjitteredDelay(attempt, config);
      final Duration jittered = SseBackoffConfig.delay(
        attempt,
        config,
        Random(42 + attempt),
      );
      expect(
        jittered.inMilliseconds,
        inInclusiveRange(
          (base.inMilliseconds * 0.8).floor(),
          (base.inMilliseconds * 1.2).ceil(),
        ),
      );
    }
  });

  test(
      'repeated stream failures enter polling fallback and recover to streaming',
      () async {
    final InMemoryLastEventIdStore store = InMemoryLastEventIdStore();
    final FakeEventHistorySource history = FakeEventHistorySource();
    final FakeSseTransport transport = FakeSseTransport()
      ..queueError(TimeoutException('tunnel black hole'))
      ..queueError(TimeoutException('tunnel black hole'))
      ..queueStream();
    // The fallback page is queued before start so the first poll is
    // deterministic.
    history.pages.add(
      EventHistoryPage(
        events: <OrchestratorEvent>[
          OrchestratorEvent.tryParse(envelopeJson(id: 10))!,
        ],
        nextCursor: null,
      ),
    );
    final SseClient client = buildClient(
      transport: transport,
      history: history,
      store: store,
      maxStreamFailures: 2,
      // Long enough that the test observes the polling status before the
      // stream probe flips it back to connected.
      pollInterval: const Duration(milliseconds: 120),
    );
    final List<int> receivedIds = <int>[];
    client.events.listen((OrchestratorEvent e) => receivedIds.add(e.id));

    await client.start();
    // Two failed opens → polling fallback.
    await waitFor(() => client.status.value == SseConnectionStatus.polling,
        reason: 'client must enter the polling fallback');

    await waitFor(() => receivedIds.contains(10),
        reason: 'polled history events must be emitted as typed events');

    // While polling, the client probes the stream; the queued live
    // connection succeeds and live events flow again.
    await waitFor(() => transport.attemptCount == 3,
        reason: 'client must probe the stream while polling');
    await waitFor(() => client.status.value == SseConnectionStatus.connected,
        reason: 'a successful probe must restore streaming');
    transport.emitTo(0, envelopeJson(id: 11));
    await waitFor(() => receivedIds.contains(11));

    expect(receivedIds, <int>[10, 11]);
    expect(store.value, 11);

    await client.dispose();
  });

  test('polling fallback requests the page after the last processed id',
      () async {
    final InMemoryLastEventIdStore store = InMemoryLastEventIdStore(7);
    final FakeEventHistorySource history = FakeEventHistorySource()
      ..pages.add(const EventHistoryPage(
          events: <OrchestratorEvent>[], nextCursor: null));
    final FakeSseTransport transport = FakeSseTransport()
      ..queueError(TimeoutException('down'))
      ..queueError(TimeoutException('down'))
      ..queueError(TimeoutException('down'));
    final SseClient client = buildClient(
      transport: transport,
      history: history,
      store: store,
      maxStreamFailures: 2,
    );

    await client.start();
    await waitFor(() => history.calls.isNotEmpty,
        reason: 'fallback must query history');
    expect(
      history.calls.first['cursor'],
      EventHistorySource.cursorForId(7),
      reason: 'the poll resumes after the last processed id',
    );

    await client.dispose();
  });

  test('cursorForId round-trips through the server encoding', () {
    // Server side: base64.urlsafe_b64encode(str(id)) minus padding
    // (apps/core/pagination.py encode_cursor); decode_cursor re-pads.
    for (final int id in <int>[0, 1, 7, 255, 123456]) {
      final String cursor = EventHistorySource.cursorForId(id);
      expect(cursor, isNot(contains('=')));
      final String padded = cursor + '=' * ((4 - cursor.length % 4) % 4);
      expect(
        String.fromCharCodes(base64Url.decode(padded)),
        '$id',
        reason: 'must decode back to the original id server-side',
      );
    }
  });

  test('a too-short stream (heartbeat timeout) is reconnected', () async {
    final FakeSseTransport transport = FakeSseTransport()
      ..queueStream()
      ..queueStream();
    final SseClient client = buildClient(
      transport: transport,
      history: FakeEventHistorySource(),
      store: InMemoryLastEventIdStore(),
      heartbeatTimeout: const Duration(milliseconds: 40),
    );

    await client.start();
    // The first connection stays silent past the heartbeat window; the
    // client must treat it as dead and reconnect (RISK-05).
    await waitFor(() => transport.openCount == 2,
        reason: 'a silent stream must be reconnected after the timeout');

    await client.dispose();
  });

  test('an auth failure stops the client instead of storming', () async {
    final FakeSseTransport transport = FakeSseTransport()
      ..queueError(unauthorizedException());
    final SseClient client = buildClient(
      transport: transport,
      history: FakeEventHistorySource(),
      store: InMemoryLastEventIdStore(),
    );

    await client.start();
    await waitFor(() => !client.isRunning);
    expect(client.status.value, SseConnectionStatus.disconnected);
    expect(transport.openCount, 0, reason: 'no retry after 401');

    await client.dispose();
  });

  test('filters are passed to the stream and to history', () async {
    final FakeSseTransport transport = FakeSseTransport()..queueStream();
    final FakeEventHistorySource history = FakeEventHistorySource()
      ..pages.add(const EventHistoryPage(
          events: <OrchestratorEvent>[], nextCursor: null));
    final SseClient client = SseClient(
      transport: transport,
      history: history,
      idStore: InMemoryLastEventIdStore(),
      projectFilter: 'PID00001',
      taskFilter: 'T-00042',
      backoff: fastBackoff(maxStreamFailures: 1),
      onWarning: (_) {},
    );

    await client.start();
    await waitFor(() => transport.openCount == 1);
    expect(transport.openedQuery.single['project'], 'PID00001');
    expect(transport.openedQuery.single['task'], 'T-00042');

    await client.dispose();
  });

  test('status is observable through every transition', () async {
    final FakeSseTransport transport = FakeSseTransport()
      ..queueError(TimeoutException('down'))
      ..queueStream();
    final SseClient client = buildClient(
      transport: transport,
      history: FakeEventHistorySource(),
      store: InMemoryLastEventIdStore(),
      maxStreamFailures: 5,
    );
    final List<SseConnectionStatus> transitions = <SseConnectionStatus>[
      client.status.value,
    ];
    void listener() => transitions.add(client.status.value);
    client.status.addListener(listener);

    await client.start();
    await waitFor(() => transport.attemptCount == 2);
    await waitFor(() => client.status.value == SseConnectionStatus.connected);

    expect(transitions, contains(SseConnectionStatus.disconnected));
    expect(transitions, contains(SseConnectionStatus.connecting));
    expect(transitions, contains(SseConnectionStatus.reconnecting));
    expect(transitions, contains(SseConnectionStatus.connected));

    client.status.removeListener(listener);
    await client.dispose();
  });
}
