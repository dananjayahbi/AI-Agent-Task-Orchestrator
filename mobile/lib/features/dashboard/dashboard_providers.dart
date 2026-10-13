import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import 'dashboard_repository.dart';
import 'dashboard_summary.dart';

/// Screen state of the Home / Overview area (Section 20.3: loading, empty,
/// error and offline-stale are separate, testable states — the widget maps
/// one-to-one).
enum DashboardStatus {
  /// First load in flight, nothing cached yet — the loading skeleton.
  loading,

  /// Loaded (or cache-served); the summary is present.
  ready,

  /// Load failed and nothing was cached — the friendly error state.
  error,
}

class DashboardState {
  const DashboardState({
    required this.status,
    this.summary,
    this.isStale = false,
    this.error,
  });

  const DashboardState.loading() : this(status: DashboardStatus.loading);

  const DashboardState.ready({
    required DashboardSummary summary,
    required bool isStale,
    OrchestratorApiException? error,
  }) : this(
          status: DashboardStatus.ready,
          summary: summary,
          isStale: isStale,
          error: error,
        );

  const DashboardState.error(OrchestratorApiException error)
      : this(status: DashboardStatus.error, error: error);

  final DashboardStatus status;
  final DashboardSummary? summary;
  final bool isStale;
  final OrchestratorApiException? error;

  bool get isEmpty => summary != null && summary!.projects.isEmpty;
}

/// Home / Overview state holder (MT-5.6-01).
///
/// Reads through [DashboardRepository] (network-first, Section 14.2 cache
/// fallback) and keeps screen states separate. No mutating affordance
/// exists here at all — the dashboard is read-only (Section 14.2).
class DashboardNotifier extends Notifier<DashboardState> {
  @override
  DashboardState build() {
    // First read constructs the notifier; the initial load is kicked off
    // explicitly by the screen (ref.read(...).refresh()) so tests stay
    // deterministic — no hidden microtasks racing assertions.
    return const DashboardState.loading();
  }

  /// Loads the summary; keeps the previous data visible while re-loading.
  Future<void> refresh() async {
    final DashboardState? previous =
        state.status == DashboardStatus.loading ? null : state;
    state = DashboardState(
      status: previous?.status ?? DashboardStatus.loading,
      summary: previous?.summary,
      isStale: previous?.isStale ?? false,
      error: previous?.error,
    );
    try {
      final DashboardSnapshot snapshot =
          await ref.read(dashboardRepositoryProvider).load();
      state = DashboardState.ready(
        summary: snapshot.summary,
        isStale: snapshot.isStale,
        error: snapshot.error,
      );
    } on OrchestratorApiException catch (error) {
      state = previous?.summary != null
          // Keep showing the data we have, honestly marked stale.
          ? DashboardState.ready(
              summary: previous!.summary!,
              isStale: true,
              error: error,
            )
          : DashboardState.error(error);
    }
  }
}

final NotifierProvider<DashboardNotifier, DashboardState> dashboardProvider =
    NotifierProvider<DashboardNotifier, DashboardState>(
  DashboardNotifier.new,
);
