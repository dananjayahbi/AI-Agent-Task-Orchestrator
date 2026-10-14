import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/orchestrator_client.dart';

/// Read/write repository behind the review sheet (WP-5.8) — every call
/// is a generated-client operation over the shared OpenAPI schema
/// (Section 14.3, NFR-11): no hand-written request layer.
///
/// Read side feeds the sheet's Section 14.1 regions; the write side is
/// exactly one operation — `POST /tasks/{id}/review` (Section 9.2) —
/// because approve / request-changes / reassign share one endpoint and
/// one Review Decision record (Section 7.2).
abstract class ReviewRepository {
  /// One task by id — `GET /tasks/{id}` (Section 9.2).
  Future<Task> fetchTask(String taskId);

  /// The task's resolutions, newest submission first — cursor-paged
  /// `GET /tasks/{id}/resolutions` followed to the end (bounded; same
  /// contract the task-detail screen consumes).
  Future<List<Resolution>> fetchResolutions(String taskId);

  /// The task's audit reports, newest first — the first page of
  /// `GET /tasks/{id}/audit-reports` is enough: the sheet shows the
  /// report for the resolution under review, and reports are ordered
  /// newest-first (Section 9.2).
  Future<List<AuditReport>> fetchAuditReports(String taskId);

  /// One stored patch — `GET /resolutions/{id}/patch` (Section 9.2);
  /// the diff region fetches this lazily (Section 14.2), never with the
  /// initial sheet load.
  Future<ResolutionPatch> fetchPatch(String resolutionId);

  /// Submit one review decision — `POST /tasks/{id}/review` (Section 9.2).
  ///
  /// [idempotencyKey] is caller-derived per logical decision
  /// (ADR-012 / NFR-12): a retried submission replays instead of
  /// recording a second decision.
  Future<ReviewDecisionResponse> submitDecision({
    required String taskId,
    required ReviewDecisionRequest request,
    required String idempotencyKey,
  });
}

/// Generated-client implementation of [ReviewRepository].
class GeneratedReviewRepository implements ReviewRepository {
  GeneratedReviewRepository(this._client);

  final OrchestratorClient _client;

  /// Safety bound for cursor loops (same rationale as the board and
  /// task-detail repositories): a runaway cursor surfaces as an honest
  /// error, never a hang.
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
  Future<List<AuditReport>> fetchAuditReports(String taskId) async {
    try {
      final Response<AuditReportListEnvelope> response =
          await _client.api.listAuditReports(
        id: taskId,
        pageSize: 25,
      );
      final AuditReportListEnvelope? envelope = response.data;
      if (envelope == null) {
        return const <AuditReport>[];
      }
      return envelope.results.toList();
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }

  @override
  Future<ResolutionPatch> fetchPatch(String resolutionId) async {
    try {
      final Response<ResolutionPatch> response =
          await _client.api.getResolutionPatch(id: resolutionId);
      final ResolutionPatch? patch = response.data;
      if (patch == null) {
        throw OrchestratorApiException.unparsed(
          message: 'Patch response carried no body.',
          retryable: true,
        );
      }
      return patch;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }

  @override
  Future<ReviewDecisionResponse> submitDecision({
    required String taskId,
    required ReviewDecisionRequest request,
    required String idempotencyKey,
  }) async {
    try {
      final Response<ReviewDecisionResponse> response =
          await _client.api.submitReviewDecision(
        id: taskId,
        reviewDecisionRequest: request,
        idempotencyKey: idempotencyKey,
      );
      final ReviewDecisionResponse? decision = response.data;
      if (decision == null) {
        throw OrchestratorApiException.unparsed(
          message: 'Review decision response carried no body.',
          retryable: true,
        );
      }
      return decision;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }
}

/// The review repository for the app; tests override it.
final Provider<ReviewRepository> reviewRepositoryProvider =
    Provider<ReviewRepository>(
  (Ref ref) => GeneratedReviewRepository(ref.watch(apiClientProvider)),
);
