import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:orchestrator_mobile/core/api/api_exception.dart';
import 'package:orchestrator_mobile/core/offline/json_cache.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_summary.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_summary_source.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

/// In-memory [JsonCache] — the Section 14.2 read-only cache seam for
/// dashboard/board tests (never a secret store; the device token never
/// goes near it).
class InMemoryJsonCache implements JsonCache {
  final Map<String, String> values = <String, String>{};
  int writeCount = 0;

  @override
  Future<String?> read(String key) async => values[key];

  @override
  Future<void> write(String key, String value) async {
    writeCount += 1;
    values[key] = value;
  }

  @override
  Future<void> remove(String key) async {
    values.remove(key);
  }
}

/// Scripted [DashboardSummarySource]: the mocked implementation behind the
/// MT-5.6-01 data-source seam (the real `GET /dashboard/summary` backend
/// endpoint does not exist yet — see the WP-5.6 changelog gap note).
class FakeDashboardSummarySource implements DashboardSummarySource {
  /// Held until the test completes it — drives the loading state.
  Completer<DashboardSummary>? pending;

  DashboardSummary? next;
  Object? nextError;
  int fetchCount = 0;

  @override
  Future<DashboardSummary> fetchSummary() async {
    fetchCount += 1;
    final Completer<DashboardSummary>? held = pending;
    if (held != null) {
      pending = null;
      return held.future;
    }
    final Object? error = nextError;
    if (error != null) {
      nextError = null;
      throw error;
    }
    final DashboardSummary? summary = next;
    if (summary == null) {
      throw StateError('FakeDashboardSummarySource: nothing scripted.');
    }
    return summary;
  }
}

/// A canonical Section 9.2 catalog error (Section 20.4 item 5) whose
/// `message` must never leak into the UI (Section 12.4).
OrchestratorApiException catalogError({
  CodeEnum code = CodeEnum.SERVER_ERROR,
  bool retryable = false,
}) =>
    OrchestratorApiException(
      statusCode: 500,
      code: code,
      message: 'raw server detail that must not be shown',
      retryable: retryable,
      details: null,
      correlationId: 'corr-1',
    );

/// A transport-level failure (no catalog envelope).
OrchestratorApiException transportError() => OrchestratorApiException.unparsed(
      message: 'connection refused',
      retryable: true,
    );

/// A dashboard summary from the given cards — Section 14.1 Home /
/// Overview contents (counts per state, velocity, active agents).
DashboardSummary summaryOf(List<ProjectDashboardCard> cards) =>
    DashboardSummary(projects: cards);

ProjectDashboardCard dashboardCard({
  required String projectId,
  required String name,
  Map<StateEnum, int> counts = const <StateEnum, int>{},
  int velocity = 0,
  int activeAgents = 0,
}) =>
    ProjectDashboardCard(
      projectId: projectId,
      name: name,
      stateCounts: counts,
      velocity: velocity,
      activeAgents: activeAgents,
    );

/// Overrides for pumping the Home / Overview screen deterministically —
/// no real HTTP, no real preferences.
List<Override> dashboardOverrides({
  required DashboardSummarySource source,
  required JsonCache cache,
}) =>
    <Override>[
      dashboardSummarySourceProvider.overrideWithValue(source),
      jsonCacheProvider.overrideWithValue(cache),
    ];
