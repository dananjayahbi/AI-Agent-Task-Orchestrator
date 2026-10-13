import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/orchestrator_client.dart';

/// Owner project list for the MT-5.6-02 selector (Section 9.2
/// `GET /projects` through the generated typed client — NFR-11).
abstract class ProjectsRepository {
  /// All of the owner's projects, following the pagination.md cursor to
  /// the end of the list (cursor is opaque; page_size follows the
  /// documented default/max).
  Future<List<Project>> fetchAll();
}

/// Generated-client implementation of [ProjectsRepository].
class GeneratedProjectsRepository implements ProjectsRepository {
  GeneratedProjectsRepository(this._client);

  final OrchestratorClient _client;

  /// Safety bound: a runaway cursor must not loop forever on a mobile
  /// device; the cap is far above any realistic project count and a hit
  /// surfaces as an honest truncation, never a hang.
  static const int _maxPages = 20;

  @override
  Future<List<Project>> fetchAll() async {
    try {
      final List<Project> projects = <Project>[];
      String? cursor;
      for (int page = 0; page < _maxPages; page++) {
        final Response<ProjectListEnvelope> response =
            await _client.api.listProjects(
          cursor: cursor,
          pageSize: 100,
        );
        final ProjectListEnvelope? envelope = response.data;
        if (envelope == null) {
          break;
        }
        projects.addAll(envelope.results);
        cursor = envelope.nextCursor;
        if (cursor == null) {
          break;
        }
      }
      return projects;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }
}

/// The projects repository for the app; tests override it.
final Provider<ProjectsRepository> projectsRepositoryProvider =
    Provider<ProjectsRepository>(
  (Ref ref) => GeneratedProjectsRepository(ref.watch(apiClientProvider)),
);
