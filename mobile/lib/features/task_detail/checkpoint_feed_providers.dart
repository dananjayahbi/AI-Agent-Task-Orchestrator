import 'dart:async';

import 'package:built_value/json_object.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/realtime/orchestrator_event.dart';
import '../../core/realtime/realtime_providers.dart';
import '../../core/realtime/sse_client.dart';
import '../../core/realtime/sse_connection_status.dart';
import 'task_detail_repository.dart';

/// Screen state of the checkpoint stream region (Section 20.3 states).
enum CheckpointFeedStatus { loading, ready, error }

/// The checkpoint stream region's state: reverse-chronological rows
/// (Section 13.2's feed spec applied to mobile) fed by the initial
/// history fetch plus live/replayed `task.checkpoint` events
/// (Sections 9.2, 9.6).
class CheckpointFeedState {
  const CheckpointFeedState({
    required this.status,
    this.checkpoints = const <Checkpoint>[],
    this.olderCursor,
    this.isDegradedPolling = false,
    this.error,
  });

  const CheckpointFeedState.loading()
      : this(status: CheckpointFeedStatus.loading);

  const CheckpointFeedState.ready({
    required List<Checkpoint> checkpoints,
    String? olderCursor,
    bool isDegradedPolling = false,
    OrchestratorApiException? error,
  }) : this(
          status: CheckpointFeedStatus.ready,
          checkpoints: checkpoints,
          olderCursor: olderCursor,
          isDegradedPolling: isDegradedPolling,
          error: error,
        );

  const CheckpointFeedState.error(OrchestratorApiException error)
      : this(status: CheckpointFeedStatus.error, error: error);

  final CheckpointFeedStatus status;

  /// Newest first — server timestamps only (Section 0.4 / Principle P7).
  final List<Checkpoint> checkpoints;

  /// Cursor for older history pages, when more exist (cursor-paged
  /// initial load — RISK-13 bounded fetch, on-demand "load older").
  final String? olderCursor;

  /// True while the shared stream client is in its documented polling
  /// fallback (Section 14.2) — the feed's visible degraded-liveness
  /// indicator; never labeled live.
  final bool isDegradedPolling;

  final OrchestratorApiException? error;

  CheckpointFeedState _copyWith({
    List<Checkpoint>? checkpoints,
    String? olderCursor,
    bool clearOlderCursor = false,
    bool? isDegradedPolling,
    OrchestratorApiException? error,
  }) =>
      CheckpointFeedState.ready(
        checkpoints: checkpoints ?? this.checkpoints,
        olderCursor:
            clearOlderCursor ? null : (olderCursor ?? this.olderCursor),
        isDegradedPolling: isDegradedPolling ?? this.isDegradedPolling,
        error: error,
      );
}

/// Poll cadence while the stream client is in its polling fallback
/// (Section 14.2 requires a fallback, not a specific cadence — chosen
/// conservative for battery/data; recorded in the WP changelog).
@visibleForTesting
const Duration checkpointPollInterval = Duration(seconds: 30);

/// Converts one Section 9.6 `task.checkpoint` event into a [Checkpoint]
/// row using only the documented wire payload (WP-1.8's
/// `write_event` data block) and the envelope's server `occurred_at`.
///
/// Returns null for anything not safely interpretable — a malformed
/// checkpoint event is skipped with no crash (Section 20.4 item 6; only
/// catalog types reach here, and unknown *shapes* are ignored).
Checkpoint? checkpointFromEvent(OrchestratorEvent event) {
  if (event.type != 'task.checkpoint') {
    return null;
  }
  final Map<String, dynamic>? data = event.data;
  final Object? id = data?['checkpoint_id'];
  if (id is! String || id.isEmpty) {
    return null;
  }
  final Object? attempt = data?['attempt_number'];
  final Object? percent = data?['percent'];
  final Object? session = data?['session_id'];
  final Object? message = data?['message'];
  final Object? kind = data?['kind'];
  final Object? usage = data?['token_usage'];
  return Checkpoint(
    (CheckpointBuilder b) => b
      ..id = id
      ..taskId = event.taskId ?? ''
      ..attemptNumber = attempt is int ? attempt : 0
      ..sessionId = session is String ? session : ''
      ..timestamp = event.occurredAt
      ..message = message is String ? message : ''
      ..percent = percent is int ? percent : null
      ..kind = kind is String && kind.isNotEmpty ? kind : 'progress'
      ..tokenUsage =
          usage is Map ? JsonObject(Map<String, dynamic>.from(usage)) : null,
  );
}

/// Server-order comparator: newest first by server timestamp, event id
/// as the deterministic tiebreak (never a client clock — P7).
int compareCheckpointsByServerTime(Checkpoint a, Checkpoint b) {
  final int byTime = b.timestamp.compareTo(a.timestamp);
  if (byTime != 0) {
    return byTime;
  }
  return b.id.compareTo(a.id);
}

/// Checkpoint feed state holder (MT-5.7-02).
///
/// **Reconciliation order (MT risk note):** the initial history fetch
/// lands first; events that arrive while it is in flight are buffered
/// and applied afterwards. Dedupe is by checkpoint id — the classic
/// history/replay double-render cannot happen (Section 9.6 "no gaps, no
/// duplicates"; background/resume replay is handled inside the shared
/// [SseClient] and arrives here through the same event path).
///
/// **Polling fallback (Section 14.2):** when the shared client reports
/// [SseConnectionStatus.polling] (stream cannot be maintained), this
/// notifier polls `GET /tasks/{id}/checkpoints` on [checkpointPollInterval]
/// and merges by id — no second stream connection is ever opened
/// ("extend, don't fork"); recovery to SSE stops the timer.
class CheckpointFeedNotifier
    extends AutoDisposeFamilyNotifier<CheckpointFeedState, String> {
  StreamSubscription<OrchestratorEvent>? _eventsSub;
  VoidCallback? _statusListener;
  Timer? _pollTimer;

  /// Checkpoint ids already in the feed — the single dedupe key across
  /// history, live events, replay and polling (Section 9.6).
  final Set<String> _seenIds = <String>{};

  /// Events that arrived before the initial history fetch settled.
  final List<Checkpoint> _pendingDuringLoad = <Checkpoint>[];

  int _loadToken = 0;
  bool _loadingOlder = false;

  /// Poll cadence — a test seam over [checkpointPollInterval].
  @visibleForTesting
  Duration pollInterval = checkpointPollInterval;

  @override
  CheckpointFeedState build(String taskId) {
    _taskId = taskId;
    final SseClient client = ref.read(sseClientProvider);
    _eventsSub = client.events
        .listen((OrchestratorEvent event) => _onEvent(taskId, event));
    _statusListener = () => _onStatusChange(client.status.value);
    client.status.addListener(_statusListener!);
    ref.onDispose(() {
      _eventsSub?.cancel();
      _eventsSub = null;
      final VoidCallback? listener = _statusListener;
      if (listener != null) {
        client.status.removeListener(listener);
        _statusListener = null;
      }
      _pollTimer?.cancel();
      _pollTimer = null;
    });
    Future<void>.microtask(load);
    return const CheckpointFeedState.loading();
  }

  late String _taskId;

  /// Initial history load (first page, newest first) and the manual
  /// refresh path.
  Future<void> load() async {
    final int token = ++_loadToken;
    try {
      final CheckpointPage page = await ref
          .read(taskDetailRepositoryProvider)
          .fetchCheckpoints(_taskId);
      if (token != _loadToken) {
        return; // Superseded refresh — drop silently.
      }
      final CheckpointFeedState current = state;
      // Dedupe by checkpoint id across history + buffered events (the
      // overlap case this MT's risk note names), then server order.
      final List<Checkpoint> merged = <Checkpoint>[];
      final Set<String> mergedIds = <String>{};
      for (final Checkpoint checkpoint in <Checkpoint>[
        ...page.checkpoints,
        ..._pendingDuringLoad
      ]) {
        if (mergedIds.add(checkpoint.id)) {
          merged.add(checkpoint);
        }
      }
      merged.sort(compareCheckpointsByServerTime);
      _seenIds
        ..clear()
        ..addAll(mergedIds);
      _pendingDuringLoad.clear();
      state = CheckpointFeedState.ready(
        checkpoints: merged,
        olderCursor: page.nextCursor,
        isDegradedPolling: current.isDegradedPolling,
      );
      // Re-sync the degraded flag: if the client entered its polling
      // fallback while this load was in flight, the timer starts now.
      _onStatusChange(ref.read(sseClientProvider).status.value);
    } on OrchestratorApiException catch (error) {
      if (token != _loadToken) {
        return;
      }
      final CheckpointFeedState current = state;
      if (current.checkpoints.isNotEmpty) {
        // A refresh that fails never replaces a good feed — the liveness
        // indicator and the next event reconcile (Section 14.2 honesty).
        state = current._copyWith(error: error);
      } else {
        state = CheckpointFeedState.error(error);
      }
    }
  }

  /// Fetches the next older history page on demand (bounded paging —
  /// RISK-13: the initial load stays one page).
  Future<void> loadOlder() async {
    final CheckpointFeedState current = state;
    final String? cursor = current.olderCursor;
    if (_loadingOlder || cursor == null) {
      return;
    }
    _loadingOlder = true;
    try {
      final CheckpointPage page = await ref
          .read(taskDetailRepositoryProvider)
          .fetchCheckpoints(_taskId, cursor: cursor);
      final List<Checkpoint> merged = <Checkpoint>[
        ...current.checkpoints,
      ];
      final Set<String> mergedIds = <String>{
        ...current.checkpoints.map((Checkpoint c) => c.id),
      };
      for (final Checkpoint checkpoint in page.checkpoints) {
        if (mergedIds.add(checkpoint.id)) {
          merged.add(checkpoint);
        }
      }
      merged.sort(compareCheckpointsByServerTime);
      _seenIds.addAll(mergedIds);
      state = current._copyWith(
        checkpoints: merged,
        olderCursor: page.nextCursor,
        clearOlderCursor: page.nextCursor == null,
      );
    } on OrchestratorApiException {
      // Older-page failure keeps the loaded feed; the button stays
      // available for a retry (never replaces good rows with an error).
    } finally {
      _loadingOlder = false;
    }
  }

  void _onEvent(String taskId, OrchestratorEvent event) {
    if (event.taskId != taskId) {
      return;
    }
    final Checkpoint? checkpoint = checkpointFromEvent(event);
    if (checkpoint == null) {
      return; // Not a checkpoint, or an unsafe shape — ignored (20.4.6).
    }
    if (state.status != CheckpointFeedStatus.ready) {
      // History has not settled yet — buffer and drain after the fetch
      // (the reconciliation order this MT's risk note demands).
      _pendingDuringLoad.add(checkpoint);
      return;
    }
    _insert(checkpoint);
  }

  /// Idempotent insert: a replayed/live-overlap duplicate is dropped by
  /// checkpoint id, then the list is re-sorted into server order.
  void _insert(Checkpoint checkpoint) {
    if (!_seenIds.add(checkpoint.id)) {
      return; // Already shown — no duplicates (Section 9.6).
    }
    final List<Checkpoint> merged = <Checkpoint>[
      ...state.checkpoints,
      checkpoint,
    ]..sort(compareCheckpointsByServerTime);
    state = state._copyWith(checkpoints: merged);
  }

  void _onStatusChange(SseConnectionStatus status) {
    final bool degraded = status == SseConnectionStatus.polling;
    if (state.status != CheckpointFeedStatus.ready) {
      return; // Nothing to indicate yet; load() re-syncs on settle.
    }
    if (degraded && _pollTimer == null) {
      state = state._copyWith(isDegradedPolling: true);
      _pollTimer = Timer.periodic(
        pollInterval,
        (Timer timer) => _pollOnce(),
      );
      _pollOnce(); // First degraded fetch is immediate.
    } else if (!degraded && _pollTimer != null) {
      _pollTimer?.cancel();
      _pollTimer = null;
      state = state._copyWith(isDegradedPolling: false);
    }
  }

  /// One degraded-mode history poll; merges by checkpoint id exactly like
  /// any other source. Failures keep the last good feed — the visible
  /// degraded indicator is the honest signal (Section 14.2).
  Future<void> _pollOnce() async {
    try {
      final CheckpointPage page = await ref
          .read(taskDetailRepositoryProvider)
          .fetchCheckpoints(_taskId);
      for (final Checkpoint checkpoint in page.checkpoints) {
        if (state.status == CheckpointFeedStatus.ready) {
          _insert(checkpoint);
        }
      }
    } on OrchestratorApiException {
      // Degraded stays degraded; the next tick or SSE recovery reconciles.
    }
  }
}

/// One checkpoint feed per task id.
final AutoDisposeNotifierProviderFamily<CheckpointFeedNotifier,
        CheckpointFeedState, String> checkpointFeedProvider =
    AutoDisposeNotifierProviderFamily<CheckpointFeedNotifier,
        CheckpointFeedState, String>(CheckpointFeedNotifier.new);
