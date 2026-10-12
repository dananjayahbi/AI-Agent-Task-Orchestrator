import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/orchestrator_client.dart';
import 'event_history_source.dart';
import 'last_event_id_store.dart';
import 'sse_client.dart';
import 'sse_transport.dart';

/// The app-wide SSE resume client (MT-5.5-05).
///
/// Built from the shared API-client [Dio] so the stream request carries the
/// MT-5.5-04 gate's device token only while the gate is unlocked, and a 401
/// on the stream flows through the same discard rule as every other call
/// (Section 12.2, ADR-006). No token value is read here.
///
/// Start/pause is driven by [SseLifecycleBinder] (foreground-only
/// streaming, Section 14.2), not by consumers — feature WPs subscribe to
/// [SseClient.events] and read [SseClient.status].
final Provider<SseClient> sseClientProvider = Provider<SseClient>(
  (ref) {
    final SseClient client = SseClient(
      transport: DioSseTransport(ref.watch(apiClientProvider).dio),
      history: DioEventHistorySource(ref.watch(apiClientProvider).dio),
      idStore: ref.watch(lastEventIdStoreProvider),
    );
    ref.onDispose(client.dispose);
    return client;
  },
);
