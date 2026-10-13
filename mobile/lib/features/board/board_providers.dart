import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/realtime/orchestrator_event.dart';
import '../../core/realtime/realtime_providers.dart';
import '../../core/realtime/sse_client.dart';
import '../../core/realtime/sse_connection_status.dart';
import 'board_cache.dart';
import 'board_event_patcher.dart';
import 'board_repository.dart';
import 'current_project.dart';

/// Screen state of the Board (MT-5.6-03; Section 20.3: loading, empty,
/// error and offline-stale are separate, testable states — the pages map
/// one-to-one).
enum BoardStatus {
  loading,
  ready,
  error,
}

class BoardState {
  const BoardState({
    required this.status,
    required this.projectId,
    this.tasks = const <Task>[],
    this.isStale = false,
    this.error,
  });

  const BoardState.loading(String? projectId)
      : this(status: BoardStatus.loading, projectId: projectId);

  const BoardState.ready({
    required String? projectId,
    required List<Task> tasks,
    required bool isStale,
    OrchestratorApiException? error,
  }) : this(
          status: BoardStatus.ready,
          projectId: projectId,
          tasks: tasks,
          isStale: isStale,
          error: error,
        );

  const BoardState.error(String? projectId, OrchestratorApiException error)
      : this(status: BoardStatus.error, projectId: projectId, error: error);

  final BoardStatus status;

  /// The project these tasks belong to — the patcher's scoping key and the
  /// race guard's discriminator (MT-5.6-02 risk note).
  final String? projectId;
  final List<Task> tasks;
  final bool isStale;
  final OrchestratorApiException? error;

  bool get isEmpty => status == BoardStatus.ready && tasks.isEmpty && !isStale;
}

/// Board state holder (MT-5.6-03 layout/data + MT-5.6-04 live patching +
/// MT-5.6-05 resume replay).
///
/// One source of truth for "what the board shows": the current project
/// ([currentProjectProvider]) drives loads, and Section 9.6 events patch
/// the loaded list through the same path whether they are live or
/// replayed (MT-5.6-05 acceptance).
///
/// The realtime subscription is **consumed, not owned**: [SseClient]
/// (MT-5.5-05) handles transport, resume, heartbeat and the polling
/// fallback; this notifier only listens to its typed events and status
/// (parent plan Section 14.2; "extend, don't fork").
class BoardNotifier extends Notifier<BoardState> {
  StreamSubscription<OrchestratorEvent>? _eventsSub;
  VoidCallback? _statusListener;

  /// Monotonic load token: a response for a superseded load (fast
  /// successive selections — MT-5.6-02 risk note) is discarded, so an
  /// older project's fetch can never overwrite the newer selection's
  /// board.
  int _loadToken = 0;

  /// Ids currently being refetched (targeted single-task refreshes) —
  /// dedupe so a burst of events for one task issues one request.
  final Set<String> _inFlightRefetches = <String>{};

  /// Highest event id whose patch has been applied (MT-5.6-05: patches
  /// are idempotent **by event id** — a replayed duplicate is skipped
  /// outright, in addition to the version guard in the patcher).
  int? _lastAppliedEventId;

  /// Event ids applied so far (capped ring) — test hook for the MT-5.6-05
  /// "counting applied events for a known missed range" acceptance.
  @visibleForTesting
  final List<int> appliedEventIds = <int>[];

  @override
  BoardState build() {
    final SseClient client = ref.read(sseClientProvider);
    // Typed events (live or replayed) flow through one patching path.
    _eventsSub = client.events.listen(_onEvent);
    // Liveness is read from the same client the transport owns — the UI
    // never fakes a live indication (Section 14.2 fallback honesty).
    _statusListener = () => _onStatusChange(client.status.value);
    client.status.addListener(_statusListener!);
    // Selection is the single source of truth (MT-5.6-02): a change
    // refetches this board and re-filters the stream (the latter done by
    // CurrentProjectNotifier.select).
    ref.listen<String?>(currentProjectProvider,
        (String? previous, String? next) {
      if (previous != next) {
        load();
      }
    });
    ref.onDispose(() {
      _eventsSub?.cancel();
      _eventsSub = null;
      final VoidCallback? listener = _statusListener;
      if (listener != null) {
        client.status.removeListener(listener);
        _statusListener = null;
      }
    });
    final String? project = ref.read(currentProjectProvider);
    Future<void>.microtask(load);
    return BoardState.loading(project);
  }

  /// Loads the current project's board (network-first, Section 14.2 cache
  /// fallback). Also the pull-to-refresh path (Section 14.1).
  Future<void> load() async {
    final String? project = ref.read(currentProjectProvider);
    final int token = ++_loadToken;
    state = BoardState.loading(project);
    if (project == null) {
      // Nothing selected: an honest empty board, not a spinner forever.
      state = const BoardState.ready(
        projectId: null,
        tasks: <Task>[],
        isStale: false,
      );
      return;
    }
    try {
      final List<Task> tasks =
          await ref.read(boardRepositoryProvider).fetchTasks(project);
      if (token != _loadToken) {
        return; // Superseded by a newer selection/load — drop silently.
      }
      await _writeCache(project, tasks);
      state = BoardState.ready(
        projectId: project,
        tasks: tasks,
        isStale: false,
      );
    } on OrchestratorApiException catch (error) {
      if (token != _loadToken) {
        return;
      }
      final List<Task>? cached = await _readCache(project);
      state = cached != null
          // Cached board, honestly marked stale (Section 14.2) — never
          // presented as live.
          ? BoardState.ready(
              projectId: project,
              tasks: cached,
              isStale: true,
              error: error,
            )
          : BoardState.error(project, error);
    }
  }

  /// Section 14.2 read-only cache helpers (MT-5.6-03 applies MT-5.6-01's
  /// pattern). Both swallow their own failures — a cache that cannot be
  /// written only costs the next offline read, and a corrupt entry reads
  /// as absent (never crashes the board).
  Future<void> _writeCache(String project, List<Task> tasks) async {
    try {
      await ref.read(boardCacheProvider).write(project, tasks);
    } catch (_) {
      // Warn-and-continue: the live load already succeeded.
    }
  }

  Future<List<Task>?> _readCache(String project) async {
    try {
      return await ref.read(boardCacheProvider).read(project);
    } catch (_) {
      return null;
    }
  }

  /// Applies one Section 9.6 event — live or replayed (MT-5.6-04/05).
  ///
  /// Idempotent by event id: a duplicate delivery (replay/live overlap)
  /// is skipped outright. The patcher's `task_version` guard is the
  /// second, data-level layer (Section 7.2).
  Future<void> _onEvent(OrchestratorEvent event) async {
    final int? lastApplied = _lastAppliedEventId;
    if (lastApplied != null && event.id <= lastApplied) {
      return; // Duplicate or out-of-order replay — already applied.
    }
    _lastAppliedEventId = event.id;
    appliedEventIds.add(event.id);

    final BoardState current = state;
    if (current.status != BoardStatus.ready ||
        current.projectId == null ||
        current.isStale) {
      // No live board to patch (nothing loaded / stale cache showing) —
      // a refetch reconciles once the board is loadable again; pure
      // patches against a stale cache would misrepresent server truth.
      return;
    }
    final BoardPatchResult result = applyEventToBoard(
      current.tasks,
      event,
      boardProjectId: current.projectId,
    );
    if (!identical(result.tasks, current.tasks)) {
      state = BoardState.ready(
        projectId: current.projectId,
        tasks: result.tasks,
        isStale: current.isStale,
        error: current.error,
      );
    }
    for (final String taskId in result.refetchTaskIds) {
      _refetchTask(taskId);
    }
  }

  /// Targeted single-task refetch (the patch-vs-refetch table's refetch
  /// half): never a board-list refetch, so live updates stay cheap
  /// (Section 13.3 discipline, mirrored from the web board).
  Future<void> _refetchTask(String taskId) async {
    final BoardState current = state;
    final String? project = current.projectId;
    if (project == null || !_inFlightRefetches.add(taskId)) {
      return;
    }
    try {
      final Task fresh =
          await ref.read(boardRepositoryProvider).fetchTask(taskId);
      final BoardState latest = state;
      if (latest.projectId != project) {
        return; // Selection moved while the refetch was in flight.
      }
      final List<Task> merged = mergeRefetchedTask(
        latest.tasks,
        fresh,
        boardProjectId: project,
      );
      if (!identical(merged, latest.tasks)) {
        state = BoardState.ready(
          projectId: latest.projectId,
          tasks: merged,
          isStale: latest.isStale,
          error: latest.error,
        );
      }
    } on OrchestratorApiException {
      // A failed targeted refresh is transient: the next event or a
      // manual refresh reconciles. Never surface a stream hiccup as a
      // board error state.
    } finally {
      _inFlightRefetches.remove(taskId);
    }
  }

  /// The client entered the documented polling fallback (stream cannot be
  /// maintained — Section 14.2, RISK-05): reconcile with a full refetch,
  /// then keep applying the polled events through the same patching path.
  /// This doubles as the MT-5.6-05 replay-failure fallback: an unusable
  /// resume id cannot be honored, the client degrades to history polling,
  /// and the board never presents a stale view as live.
  void _onStatusChange(SseConnectionStatus status) {
    if (status == SseConnectionStatus.polling) {
      load();
    }
  }
}

final NotifierProvider<BoardNotifier, BoardState> boardProvider =
    NotifierProvider<BoardNotifier, BoardState>(BoardNotifier.new);
