import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/orchestrator_client.dart';
import 'dashboard_summary.dart';

/// Dashboard backend seam (MT-5.6-01; Section 9.2 `GET /dashboard/summary`,
/// Owner).
///
/// Tests replace this seam with a scripted fake; the Dio implementation is
/// the only place real calls are made (NFR-11 discipline).
abstract class DashboardSummarySource {
  Future<DashboardSummary> fetchSummary();
}

/// Dio-backed source against the shared API client's [Dio] — same
/// interceptors as every other call: error mapping to the Section 9.2
/// envelope, correlation ids, and the gate's device token only while
/// unlocked (ADR-006). The typed generated client does not cover
/// `/dashboard/summary` yet (no backend endpoint / schema path — see the
/// model's contract note); the hand-written half here is parsing, not
/// endpoint models. Reported as an NFR-11 follow-up in the changelog.
class DioDashboardSummarySource implements DashboardSummarySource {
  DioDashboardSummarySource(this._dio);

  final Dio _dio;

  static const String summaryPath = '/api/v1/dashboard/summary';

  @override
  Future<DashboardSummary> fetchSummary() async {
    try {
      final Response<Map<String, dynamic>> response =
          await _dio.get<Map<String, dynamic>>(summaryPath);
      final DashboardSummary? summary =
          DashboardSummary.tryParse(response.data ?? const <String, dynamic>{});
      if (summary == null) {
        // Payload did not match the documented shape: surface an honest
        // error, never an empty dashboard pretending to be real (20.3).
        throw OrchestratorApiException.unparsed(
          message: 'Dashboard summary payload did not match the '
              'documented shape.',
          retryable: false,
        );
      }
      return summary;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }
}

/// The dashboard seam for the app; tests override it.
final Provider<DashboardSummarySource> dashboardSummarySourceProvider =
    Provider<DashboardSummarySource>(
  (Ref ref) => DioDashboardSummarySource(ref.watch(apiClientProvider).dio),
);
