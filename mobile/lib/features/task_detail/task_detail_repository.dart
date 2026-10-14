import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/orchestrator_client.dart';

/// Read-side repository for the Task detail screen (MT-5.7-01) and its
/// regions (MT-5.7-02 checkpoints, MT-5.7-03 attachments) — every call is
/// a generated-client operation over the shared OpenAPI schema
/// (Section 14.3, NFR-11): no hand-written request layer.
abstract class TaskDetailRepository {
  /// One task by id — `GET /tasks/{id}` (Section 9.2).
  Future<Task> fetchTask(String taskId);

  /// The task's resolutions, newest submission first — cursor-paged
  /// `GET /tasks/{id}/resolutions` followed to the end (bounded).
  Future<List<Resolution>> fetchResolutions(String taskId);

  /// One page of the task's checkpoint history, newest first —
  /// `GET /tasks/{id}/checkpoints` (Section 9.2; MT-5.7-02's initial
  /// history and polling fallback).
  Future<CheckpointPage> fetchCheckpoints(
    String taskId, {
    String? cursor,
    int pageSize = 25,
  });

  /// The task's attachments — cursor-paged `GET /tasks/{id}/attachments`
  /// followed to the end (bounded; MT-5.7-03).
  Future<List<Attachment>> fetchAttachments(String taskId);
}

/// One cursor page of checkpoint history (pagination.md envelope).
class CheckpointPage {
  const CheckpointPage({required this.checkpoints, this.nextCursor});

  final List<Checkpoint> checkpoints;
  final String? nextCursor;
}

/// Generated-client implementation of [TaskDetailRepository].
class GeneratedTaskDetailRepository implements TaskDetailRepository {
  GeneratedTaskDetailRepository(this._client);

  final OrchestratorClient _client;

  /// Safety bound for cursor loops (same rationale as the board
  /// repository): a runaway cursor surfaces as an honest error, never a
  /// hang.
  static const int _maxPages = 50;

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

  @override
  Future<List<Resolution>> fetchResolutions(String taskId) async {
    try {
      final List<Resolution> resolutions = <Resolution>[];
      String? cursor;
      for (int page = 0; page < _maxPages; page++) {
        final Response<ResolutionListEnvelope> response =
            await _client.api.listResolutions(
          id: taskId,
          cursor: cursor,
          pageSize: 100,
        );
        final ResolutionListEnvelope? envelope = response.data;
        if (envelope == null) {
          break;
        }
        resolutions.addAll(envelope.results);
        cursor = envelope.nextCursor;
        if (cursor == null) {
          break;
        }
      }
      return resolutions;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }

  @override
  Future<CheckpointPage> fetchCheckpoints(
    String taskId, {
    String? cursor,
    int pageSize = 25,
  }) async {
    try {
      final Response<CheckpointListEnvelope> response =
          await _client.api.listCheckpoints(
        id: taskId,
        cursor: cursor,
        pageSize: pageSize,
      );
      final CheckpointListEnvelope? envelope = response.data;
      if (envelope == null) {
        return const CheckpointPage(checkpoints: <Checkpoint>[]);
      }
      return CheckpointPage(
        checkpoints: envelope.results.toList(),
        nextCursor: envelope.nextCursor,
      );
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }

  @override
  Future<List<Attachment>> fetchAttachments(String taskId) async {
    try {
      final List<Attachment> attachments = <Attachment>[];
      String? cursor;
      for (int page = 0; page < _maxPages; page++) {
        final Response<AttachmentListEnvelope> response =
            await _client.api.listTaskAttachments(
          id: taskId,
          cursor: cursor,
          pageSize: 100,
        );
        final AttachmentListEnvelope? envelope = response.data;
        if (envelope == null) {
          break;
        }
        attachments.addAll(envelope.results);
        cursor = envelope.nextCursor;
        if (cursor == null) {
          break;
        }
      }
      return attachments;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }
}

/// The task-detail repository for the app; tests override it.
final Provider<TaskDetailRepository> taskDetailRepositoryProvider =
    Provider<TaskDetailRepository>(
  (Ref ref) => GeneratedTaskDetailRepository(ref.watch(apiClientProvider)),
);
