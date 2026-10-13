import 'package:built_value/serializer.dart';
import 'package:orchestrator_mobile/core/realtime/orchestrator_event.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

/// Catalog-only discipline (Section 20.4 item 6; MT-5.6-04 acceptance):
/// the closed Section 9.6 event catalog. Anything not listed here is not a
/// known event type and is ignored without breaking the stream.
const Set<String> kCatalogEventTypes = <String>{
  'project.created',
  'project.updated',
  'task.created',
  'task.updated',
  'task.transitioned',
  'task.claimed',
  'task.released',
  'task.checkpoint',
  'task.lease_expiring',
  'task.lease_expired',
  'attachment.processing',
  'attachment.ready',
  'attachment.failed',
  'audit.claimed',
  'audit.passed',
  'audit.escalated',
  'review.requested',
  'review.decided',
  'merge.started',
  'merge.succeeded',
  'merge.failed',
  'agent.session_started',
  'agent.session_ended',
  'system.alert',
};

/// Event → board patch (MT-5.6-04; parent plan Section 9.6 envelope,
/// Section 7.2 `version` optimistic concurrency).
///
/// Patch-vs-refetch table (same documented split as the web board's
/// MT-4.3-05 reducer; the backend's event payloads are deliberately
/// minimal — transitions carry `{from_state, to_state, reason_code,
/// task_version}` only, never a full row):
///
///  | event                       | handling                                     |
///  |-----------------------------|----------------------------------------------|
///  | task.transitioned           | pure in-place patch: state + version         |
///  | task.lease_expired          | pure patch: state + version + lease/worker   |
///  |                             | cleared (Section 8.3 invariant 1)             |
///  | task.lease_expiring         | pure patch: lease_expires_at refresh         |
///  | task.checkpoint             | pure patch: last_checkpoint_at               |
///  | task.claimed / task.released| pure patch of state+version, plus a          |
///  |                             | **targeted single-task refetch** for the     |
///  |                             | worker/lease fields the payload omits        |
///  | task.created / task.updated | **targeted single-task refetch** (payload has |
///  |                             | no row data / changed field values)          |
///  | audit.passed, merge.*       | **targeted single-task refetch** (merge       |
///  |                             | badge fields; payload undefined until WP-3.x) |
///  | everything else             | ignored (out of board scope)                  |
///
/// Version discipline (Section 7.2): a pure patch whose `task_version` is
/// older than the cached one is **ignored outright** — newer local data
/// never regresses (MT-5.6-04 acceptance "stale-version ignored").
/// Patches are idempotent by construction, so a reconnect replay
/// (MT-5.6-05) applies missed events exactly right the second time — no
/// duplicate cards, no gaps (Section 9.6).
///
/// Pure function: returns the (possibly unchanged) task list plus the ids
/// needing a targeted refetch; the caller owns state and network.
class BoardPatchResult {
  const BoardPatchResult({required this.tasks, required this.refetchTaskIds});

  final List<Task> tasks;

  /// Task rows the event payload cannot fully describe — refetch these
  /// via `GET /tasks/{id}` (never a board-list refetch).
  final List<String> refetchTaskIds;
}

/// Event types handled as pure patches (no network).
const Set<String> _purePatchEvents = <String>{
  'task.transitioned',
  'task.lease_expired',
  'task.lease_expiring',
  'task.checkpoint',
};

/// Event types that schedule a targeted single-task refetch (some also
/// carry a pure patch of the fields they do document).
const Set<String> _refetchEvents = <String>{
  'task.created',
  'task.updated',
  'task.claimed',
  'task.released',
  'audit.passed',
  'merge.started',
  'merge.succeeded',
  'merge.failed',
};

/// Applies one Section 9.6 event to the cached board task list. Pure and
/// defensive: unknown catalog types, foreign-project events, malformed
/// payloads and stale versions all resolve to "no change" without
/// throwing (MT-5.6-04 acceptance items 4/6; MT-5.6-05 duplicate/out-of-
/// order handling).
///
/// [boardProjectId] scopes the patch: the stream carries the selected
/// project's filter (Section 9.6) but a replay or filter switch can still
/// deliver foreign events — they must never land on this board.
BoardPatchResult applyEventToBoard(
  List<Task> tasks,
  OrchestratorEvent event, {
  required String? boardProjectId,
}) {
  if (!kCatalogEventTypes.contains(event.type)) {
    return BoardPatchResult(tasks: tasks, refetchTaskIds: const <String>[]);
  }
  final String? taskId = event.taskId;
  if (taskId == null) {
    return BoardPatchResult(tasks: tasks, refetchTaskIds: const <String>[]);
  }
  // Foreign-project event (filter switch race, replay overlap): ignore.
  final String? eventProjectId = event.projectId;
  if (boardProjectId != null &&
      eventProjectId != null &&
      eventProjectId != boardProjectId) {
    return BoardPatchResult(tasks: tasks, refetchTaskIds: const <String>[]);
  }

  final int index = tasks.indexWhere((Task task) => task.id == taskId);
  final Map<String, dynamic> data = event.data ?? const <String, dynamic>{};
  final int? eventVersion = _readTaskVersion(data);

  if (_purePatchEvents.contains(event.type) ||
      _refetchEvents.contains(event.type)) {
    final bool refetch = _refetchEvents.contains(event.type);

    if (index == -1) {
      // Nothing cached to move for pure patches; creation/update gaps
      // arrive via a targeted refetch.
      return BoardPatchResult(
        tasks: tasks,
        refetchTaskIds: refetch ? <String>[taskId] : const <String>[],
      );
    }
    final Task cached = tasks[index];
    if (_isStaleAgainst(eventVersion, cached)) {
      // Section 7.2: an event older than the cache must never regress it.
      return BoardPatchResult(tasks: tasks, refetchTaskIds: const <String>[]);
    }

    Task patched = cached;
    if (event.type == 'task.checkpoint') {
      patched = cached.rebuild((TaskBuilder b) {
        final String? current = cached.lastCheckpointAt?.toIso8601String();
        final String occurred = event.occurredAt.toIso8601String();
        if (current == null || occurred.compareTo(current) > 0) {
          b.lastCheckpointAt = event.occurredAt;
        }
      });
    } else if (event.type == 'task.lease_expiring') {
      final Object? expiresAt = data['lease_expires_at'];
      if (expiresAt is String) {
        final DateTime? parsed = DateTime.tryParse(expiresAt);
        if (parsed != null) {
          patched = cached.rebuild(
            (TaskBuilder b) => b.leaseExpiresAt = parsed.toUtc(),
          );
        }
      }
    } else {
      // task.transitioned / task.lease_expired / claimed / released:
      // move columns from to_state when the payload documents it.
      final StateEnum? toState = _stateFromWire(data['to_state']);
      if (toState != null) {
        final bool leavingLease = event.type == 'task.lease_expired' ||
            toState != StateEnum.inProgress;
        patched = cached.rebuild((TaskBuilder b) {
          b.state = toState;
          if (eventVersion != null) {
            b.version = eventVersion;
          }
          if (leavingLease) {
            // Section 8.3 invariant 1: no coder lease outside in_progress.
            b.workerAgentId = null;
            b.workerSessionId = null;
            b.claimedRole = null;
            b.leaseAcquiredAt = null;
            b.leaseExpiresAt = null;
          }
        });
      }
    }

    final List<Task> next = List<Task>.of(tasks);
    next[index] = patched;
    return BoardPatchResult(
      tasks: next,
      // Claimed/released and audit/merge events also refresh the fields
      // the payload omits (worker/lease, merge badge) via refetch.
      refetchTaskIds: refetch ? <String>[taskId] : const <String>[],
    );
  }

  // Catalog type outside board scope (project.*, attachment.*, other
  // audit.*, review.*, agent.*, system.alert): ignore without breaking
  // the stream (Section 20.4 item 6).
  return BoardPatchResult(tasks: tasks, refetchTaskIds: const <String>[]);
}

/// Merges a freshly refetched task row into the cached list. Insert-or-
/// update: a row the board does not know yet appears in its canonical
/// page (MT-5.6-05 "a task missed entirely while suspended appears after
/// replay"); a known row is replaced; an archived row is dropped (T19
/// default board visibility).
List<Task> mergeRefetchedTask(
  List<Task> tasks,
  Task fresh, {
  required String? boardProjectId,
}) {
  if (fresh.archivedAt != null) {
    return tasks.where((Task task) => task.id != fresh.id).toList();
  }
  if (boardProjectId != null && fresh.projectId != boardProjectId) {
    return tasks;
  }
  final int index = tasks.indexWhere((Task task) => task.id == fresh.id);
  if (index == -1) {
    return <Task>[...tasks, fresh];
  }
  // Server truth wins on refetch — but an out-of-order older row must not
  // regress a newer cached one (defensive, MT-5.6-05).
  if (fresh.version < tasks[index].version) {
    return tasks;
  }
  final List<Task> next = List<Task>.of(tasks);
  next[index] = fresh;
  return next;
}

int? _readTaskVersion(Map<String, dynamic> data) {
  final Object? version = data['task_version'];
  return version is int ? version : null;
}

/// Section 7.2 optimistic concurrency: an event older than the cached row
/// is stale; an equal version is a replay of something already applied
/// (idempotent either way).
bool _isStaleAgainst(int? eventVersion, Task cached) =>
    eventVersion != null && eventVersion < cached.version;

/// Wire string → canonical enum through the generated serializers
/// (G-01: the schema owns the mapping, no hand-copied state strings).
StateEnum? _stateFromWire(Object? wire) {
  if (wire is! String) {
    return null;
  }
  try {
    return standardSerializers.deserialize(
      wire,
      specifiedType: const FullType(StateEnum),
    ) as StateEnum;
  } catch (_) {
    return null;
  }
}
