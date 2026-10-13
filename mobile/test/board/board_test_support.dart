import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:orchestrator_mobile/core/offline/json_cache.dart';
import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/features/board/board_repository.dart';
import 'package:orchestrator_mobile/features/board/projects_repository.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';

/// A well-formed generated [Task] for fixtures — every required Section
/// 7.2 field, canonical [StateEnum] value, no hand-built JSON anywhere.
/// [projectId] defaults to the suite's standard project.
Task makeTask({
  required String id,
  String projectId = 'PID00001',
  StateEnum state = StateEnum.pending,
  PriorityEnum priority = PriorityEnum.medium,
  int version = 1,
  String? workerAgentId,
  int attemptNumber = 1,
  String mergeStatus = 'none',
  String title = 'A task',
}) =>
    Task(
      (TaskBuilder b) => b
        ..id = id
        ..projectId = projectId
        ..title = title
        ..description = 'description'
        ..acceptanceCriteria.replace(const <String>['acceptance criteria'])
        ..targetScope.replace(const <String>['src/**'])
        ..testCommand = 'flutter test'
        ..priority = priority
        ..state = state
        ..version = version
        ..workerAgentId = workerAgentId
        ..attemptNumber = attemptNumber
        ..failureRetryCount = 0
        ..auditRequired = false
        ..latestFeedback = ''
        ..mergeStatus = mergeStatus
        ..createdAt = DateTime.utc(2026, 10, 1)
        ..updatedAt = DateTime.utc(2026, 10, 2),
    );

/// A well-formed generated [Project] for selector fixtures.
Project makeProject({
  required String id,
  required String name,
  ActiveStatusEnum activeStatus = ActiveStatusEnum.active,
}) =>
    Project(
      (ProjectBuilder b) => b
        ..id = id
        ..name = name
        ..repoPath = 'org/repo'
        ..activeStatus = activeStatus
        ..defaultBranch = 'main'
        ..systemPromptRules = ''
        ..agentPolicy = 0
        ..taskCounter = 0
        ..createdAt = DateTime.utc(2026, 10, 1)
        ..updatedAt = DateTime.utc(2026, 10, 1),
    );

/// Scripted [ProjectsRepository] for the MT-5.6-02 selector.
class FakeProjectsRepository implements ProjectsRepository {
  List<Project> projects = <Project>[];
  Object? nextError;
  int fetchCount = 0;

  @override
  Future<List<Project>> fetchAll() async {
    fetchCount += 1;
    final Object? error = nextError;
    if (error != null) {
      nextError = null;
      throw error;
    }
    return projects;
  }
}

/// Scripted [BoardRepository]: per-project task lists plus a targeted
/// single-task refetch table (MT-5.6-04 patch-vs-refetch).
class FakeBoardRepository implements BoardRepository {
  /// Tasks per project id; [fetchTasks] serves the current entry.
  final Map<String, List<Task>> tasksByProject = <String, List<Task>>{};

  /// Fresh rows for targeted `GET /tasks/{id}` refetches.
  final Map<String, Task> singleTasks = <String, Task>{};

  Object? nextError;
  final List<String> taskListCalls = <String>[];
  final List<String> singleTaskCalls = <String>[];

  /// When set, [fetchTasks] parks until completed (drives loading states).
  Completer<void>? held;

  int listCallsFor(String projectId) =>
      taskListCalls.where((String id) => id == projectId).length;

  @override
  Future<List<Task>> fetchTasks(String projectId) async {
    taskListCalls.add(projectId);
    final Completer<void>? gate = held;
    if (gate != null) {
      held = null;
      await gate.future;
    }
    final Object? error = nextError;
    if (error != null) {
      nextError = null;
      throw error;
    }
    return tasksByProject[projectId] ?? <Task>[];
  }

  @override
  Future<Task> fetchTask(String taskId) async {
    singleTaskCalls.add(taskId);
    final Object? error = nextError;
    if (error != null) {
      nextError = null;
      throw error;
    }
    final Task? task = singleTasks[taskId];
    if (task == null) {
      throw StateError('FakeBoardRepository: no single task $taskId.');
    }
    return task;
  }
}

/// A real [SseClient] on scripted fakes — the MT-5.5-05 transport reused
/// verbatim by WP-5.6 (no forked stream client); tests emit frames through
/// [FakeSseTransport] exactly like the server would.
SseClient buildTestSseClient({
  required FakeSseTransport transport,
  FakeEventHistorySource? history,
  InMemoryLastEventIdStore? store,
  int maxStreamFailures = 3,
  Duration pollInterval = const Duration(milliseconds: 5),
}) {
  return SseClient(
    transport: transport,
    history: history ?? FakeEventHistorySource(),
    idStore: store ?? InMemoryLastEventIdStore(),
    backoff: fastBackoff(
      maxStreamFailures: maxStreamFailures,
      pollInterval: pollInterval,
    ),
    heartbeatTimeout: const Duration(seconds: 30),
    onWarning: (_) {},
  );
}

/// Overrides for pumping Board-side widgets deterministically — no real
/// HTTP, no real preferences, no real stream.
List<Override> boardOverrides({
  required FakeProjectsRepository projects,
  required FakeBoardRepository board,
  JsonCache? cache,
  SseClient? sseClient,
}) =>
    <Override>[
      projectsRepositoryProvider.overrideWithValue(projects),
      boardRepositoryProvider.overrideWithValue(board),
      jsonCacheProvider.overrideWithValue(cache ?? InMemoryJsonCache()),
      sseClientProvider.overrideWithValue(
        sseClient ?? buildTestSseClient(transport: FakeSseTransport()),
      ),
    ];
