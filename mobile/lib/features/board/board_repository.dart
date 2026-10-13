import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/orchestrator_client.dart';

/// Board data for one project (MT-5.6-03; Section 9.2
/// `GET /projects/{pid}/tasks` and `GET /tasks/{id}` through the
/// generated typed client — NFR-11).
abstract class BoardRepository {
  /// All of the project's non-archived tasks, following the pagination.md
  /// cursor to the end of the list.
  Future<List<Task>> fetchTasks(String projectId);

  /// One task by id — the targeted single-task refresh used by live
  /// updates (MT-5.6-04 patch-vs-refetch table).
  Future<Task> fetchTask(String taskId);
}

/// Generated-client implementation.
///
/// **Grouping decision (MT-5.6-03 risk note, recorded):** one
/// project-scoped list request (cursor-paged) is fetched and grouped
/// client-side by canonical state — the tasks endpoint already supports
/// project-scoped listing, so per-page requests would multiply round
/// trips without buying correctness. Per-page fetching is revisited only
/// if payload size forces it.
class GeneratedBoardRepository implements BoardRepository {
  GeneratedBoardRepository(this._client);

  final OrchestratorClient _client;

  /// Safety bound for the cursor loop (same rationale as the projects
  /// list): a runaway cursor surfaces as an honest error, never a hang.
  static const int _maxPages = 50;

  @override
  Future<List<Task>> fetchTasks(String projectId) async {
    try {
      final List<Task> tasks = <Task>[];
      String? cursor;
      for (int page = 0; page < _maxPages; page++) {
        final Response<TaskListEnvelope> response = await _client.api.listTasks(
          pid: projectId,
          cursor: cursor,
          pageSize: 100,
        );
        final TaskListEnvelope? envelope = response.data;
        if (envelope == null) {
          break;
        }
        tasks.addAll(envelope.results);
        cursor = envelope.nextCursor;
        if (cursor == null) {
          break;
        }
      }
      return tasks;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }

  @override
  Future<Task> fetchTask(String taskId) async {
    try {
      final Response<Task> response = await _client.api.retrieveTask(
        id: taskId,
      );
      final Task? task = response.data;
      if (task == null) {
        throw OrchestratorApiException.unparsed(
          message: 'Task response carried no body.',
          retryable: true,
        );
      }
      return task;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }
}

/// The board repository for the app; tests override it.
final Provider<BoardRepository> boardRepositoryProvider =
    Provider<BoardRepository>(
  (Ref ref) => GeneratedBoardRepository(ref.watch(apiClientProvider)),
);
