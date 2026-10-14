import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/realtime/orchestrator_event.dart';
import '../../core/realtime/realtime_providers.dart';
import '../../core/realtime/sse_client.dart';
import '../board/board_cache.dart';
import 'task_detail_repository.dart';

/// Screen state of the Task detail (Section 20.3: loading, ready and
/// error are separate, testable states; the offline-cached view is a
/// ready sub-state, Section 14.2).
enum TaskDetailStatus { loading, ready, error }

/// Everything the detail screen renders, per Section 14.1's row: the task
/// summary/criteria fields come from [task], the resolutions list is
/// loaded alongside it; the checkpoint stream and attachments own their
/// own providers (MT-5.7-02/03) and their regions on the screen.
class TaskDetailState {
  const TaskDetailState({
    required this.status,
    this.task,
    this.resolutions = const <Resolution>[],
    this.isStale = false,
    this.error,
  });

  const TaskDetailState.loading() : this(status: TaskDetailStatus.loading);

  const TaskDetailState.ready({
    required Task task,
    required List<Resolution> resolutions,
    bool isStale = false,
    OrchestratorApiException? error,
  }) : this(
          status: TaskDetailStatus.ready,
          task: task,
          resolutions: resolutions,
          isStale: isStale,
          error: error,
        );

  const TaskDetailState.error(OrchestratorApiException error)
      : this(status: TaskDetailStatus.error, error: error);

  final TaskDetailStatus status;
  final Task? task;
  final List<Resolution> resolutions;

  /// True when [task] came from the read-only cache after a failed
  /// network load — presented honestly stale, never as live
  /// (Section 14.2; MT-5.7-01 risk note, decision recorded in the WP
  /// changelog: the board cache already stores full generated [Task]
  /// rows, so the task *summary* is cacheable in v1 without a second
  /// cache; resolutions are not cached and load live-only).
  final bool isStale;
  final OrchestratorApiException? error;
}

/// Section 9.6 event types that change the task row enough to deserve a
/// targeted single-task refetch (the web detail's patch-vs-refetch table,
/// mirrored: mobile refetches the row rather than interpreting payloads).
const Set<String> taskRowRefetchEvents = <String>{
  'task.updated',
  'task.transitioned',
  'task.claimed',
  'task.released',
};

/// Task detail state holder (MT-5.7-01).
///
/// One notifier per task id (Riverpod family — the single established
/// state-management pattern). The realtime subscription is consumed, not
/// owned: [SseClient] (MT-5.5-05) handles transport, resume and the
/// polling fallback; this notifier only listens for this task's
/// row-changing events and refetches the row (never the whole screen).
class TaskDetailNotifier
    extends AutoDisposeFamilyNotifier<TaskDetailState, String> {
  StreamSubscription<OrchestratorEvent>? _eventsSub;

  /// In-flight row refetch guard: an event burst results in one request.
  bool _rowRefetchInFlight = false;

  /// Monotonic load token — a response for a superseded load is dropped.
  int _loadToken = 0;

  @override
  TaskDetailState build(String taskId) {
    _taskId = taskId;
    final SseClient client = ref.read(sseClientProvider);
    _eventsSub = client.events
        .listen((OrchestratorEvent event) => _onEvent(taskId, event));
    ref.onDispose(() {
      _eventsSub?.cancel();
      _eventsSub = null;
    });
    Future<void>.microtask(load);
    return const TaskDetailState.loading();
  }

  /// The family argument, retained for reloads and refetches.
  late String _taskId;

  /// Loads the task row and its resolutions (network-first; the failed
  /// load falls back to the cached board row for an honest stale view).
  Future<void> load() async {
    final String taskId = _taskId;
    final int token = ++_loadToken;
    try {
      final TaskDetailRepository repository =
          ref.read(taskDetailRepositoryProvider);
      final Task task = await repository.fetchTask(taskId);
      final List<Resolution> resolutions =
          await repository.fetchResolutions(taskId);
      if (token != _loadToken) {
        return; // Superseded — drop silently.
      }
      state = TaskDetailState.ready(task: task, resolutions: resolutions);
    } on OrchestratorApiException catch (error) {
      if (token != _loadToken) {
        return;
      }
      final Task? cached = await _readCachedTask(taskId);
      state = cached != null
          ? TaskDetailState.ready(
              task: cached,
              resolutions: const <Resolution>[],
              isStale: true,
              error: error,
            )
          : TaskDetailState.error(error);
    }
  }

  /// Section 14.2 read-only cache: the board already cached this task's
  /// full row for its project; derive the project id from the canonical
  /// `{PID}-T{index}` task id (Section 7.3) and look the row up there.
  Future<Task?> _readCachedTask(String taskId) async {
    final int cut = taskId.lastIndexOf('-T');
    if (cut <= 0) {
      return null; // Not a canonical task id — no honest cache key.
    }
    final String projectId = taskId.substring(0, cut);
    try {
      final List<Task>? tasks =
          await ref.read(boardCacheProvider).read(projectId);
      if (tasks == null) {
        return null;
      }
      for (final Task task in tasks) {
        if (task.id == taskId) {
          return task;
        }
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  void _onEvent(String taskId, OrchestratorEvent event) {
    if (event.taskId != taskId || !taskRowRefetchEvents.contains(event.type)) {
      return; // Another task's event, or a catalog type this screen ignores.
    }
    _refetchRow(taskId);
  }

  /// Targeted `GET /tasks/{id}` refetch on row-changing events — one
  /// request per burst, never a resolutions reload (Section 13.3
  /// discipline mirrored from the web detail).
  Future<void> _refetchRow(String taskId) async {
    if (_rowRefetchInFlight) {
      return;
    }
    _rowRefetchInFlight = true;
    try {
      final Task fresh =
          await ref.read(taskDetailRepositoryProvider).fetchTask(taskId);
      final TaskDetailState current = state;
      if (current.status == TaskDetailStatus.ready) {
        state = TaskDetailState.ready(
          task: fresh,
          resolutions: current.resolutions,
          isStale: current.isStale,
          error: current.error,
        );
      }
    } on OrchestratorApiException {
      // The stream keeps working; the next event or manual reload
      // reconciles. Never replace a good screen with a transient error.
    } finally {
      _rowRefetchInFlight = false;
    }
  }
}

/// One detail screen per task id.
final AutoDisposeNotifierProviderFamily<TaskDetailNotifier, TaskDetailState,
        String> taskDetailProvider =
    AutoDisposeNotifierProviderFamily<TaskDetailNotifier, TaskDetailState,
        String>(TaskDetailNotifier.new);
