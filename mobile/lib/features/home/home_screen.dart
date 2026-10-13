import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/nav_shell.dart';
import '../../core/api/api_exception.dart';
import '../../core/api/read_error_messages.dart';
import '../../core/realtime/orchestrator_event.dart';
import '../../core/realtime/realtime_providers.dart';
import '../../core/realtime/sse_client.dart';
import '../../core/realtime/sse_connection_status.dart';
import '../board/board_event_patcher.dart';
import '../board/current_project.dart';
import '../dashboard/dashboard_providers.dart';
import '../dashboard/dashboard_summary.dart';
import '../dashboard/project_card.dart';

/// Home / Overview area (MT-5.6-01; parent plan Section 14.1): project
/// cards with per-state counts, velocity and active agents, plus the
/// "needs review" banner — all consumed from `GET /dashboard/summary`
/// through the dashboard repository (Section 9.2).
///
/// States are kept separate per Section 20.3: a loading skeleton, an
/// empty state (no projects), a friendly error state, and a stale-from-
/// cache presentation (Section 14.2 read-only offline cache) that is
/// never presented as live. The screen is read-only: no mutating
/// affordance exists here (Section 14.2).
///
/// The whole navigator sits behind the WP-5.5 biometric gate
/// (`LockGate` in app.dart), so this screen renders only while unlocked
/// (Section 14.2).
///
/// Live updates (MT-5.6-04): while foregrounded, catalog events from the
/// shared SSE client debounced-refresh the summary so card counts follow
/// server truth (the summary endpoint is the single source — never
/// client-assembled numbers); entering the polling fallback reconciles
/// with one refresh too (Section 14.2). The shell keeps this screen
/// mounted across tabs, so updates land even while the user is
/// elsewhere.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _loadStarted = false;
  StreamSubscription<OrchestratorEvent>? _eventsSub;
  SseClient? _client;
  VoidCallback? _statusListener;
  Timer? _refreshDebounce;

  @override
  void initState() {
    super.initState();
    final client = ref.read(sseClientProvider);
    _client = client;
    _eventsSub = client.events.listen(_onStreamEvent);
    _statusListener = () {
      // Entering the documented fallback: reconcile once; subsequent
      // polled events refresh through the same debounce.
      if (client.status.value == SseConnectionStatus.polling) {
        _scheduleRefresh();
      }
    };
    client.status.addListener(_statusListener!);
  }

  @override
  void dispose() {
    _eventsSub?.cancel();
    _eventsSub = null;
    final VoidCallback? listener = _statusListener;
    if (listener != null) {
      _client?.status.removeListener(listener);
      _statusListener = null;
    }
    _refreshDebounce?.cancel();
    _refreshDebounce = null;
    super.dispose();
  }

  void _onStreamEvent(OrchestratorEvent event) {
    if (!kCatalogEventTypes.contains(event.type)) {
      return; // Non-catalog noise never pokes the dashboard.
    }
    _scheduleRefresh();
  }

  /// Debounced so an event burst costs at most one summary fetch; the
  /// refresh no-ops while loading or while honestly showing stale cache.
  void _scheduleRefresh() {
    _refreshDebounce?.cancel();
    _refreshDebounce = Timer(const Duration(milliseconds: 250), () {
      _refreshDebounce = null;
      if (!mounted) {
        return;
      }
      final DashboardState state = ref.read(dashboardProvider);
      if (state.status == DashboardStatus.ready && !state.isStale) {
        ref.read(dashboardProvider.notifier).refresh();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final DashboardState state = ref.watch(dashboardProvider);
    if (!_loadStarted && state.status == DashboardStatus.loading) {
      _loadStarted = true;
      // Explicit initial load (no hidden microtask): kicked off after the
      // first frame; refresh/retry reuse the same path.
      Future<void>.microtask(ref.read(dashboardProvider.notifier).refresh);
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('Home / Overview'),
        actions: <Widget>[
          IconButton(
            key: const ValueKey<String>('dashboard-refresh'),
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(dashboardProvider.notifier).refresh(),
          ),
        ],
      ),
      body: _body(state),
    );
  }

  Widget _body(DashboardState state) {
    switch (state.status) {
      case DashboardStatus.loading:
        return const _LoadingSkeleton();
      case DashboardStatus.error:
        return _ErrorState(
          message: friendlyReadErrorMessage(state.error!),
          onRetry: () => ref.read(dashboardProvider.notifier).refresh(),
        );
      case DashboardStatus.ready:
        final DashboardSummary summary = state.summary!;
        if (summary.projects.isEmpty) {
          return const _EmptyState();
        }
        return RefreshIndicator(
          onRefresh: () => ref.read(dashboardProvider.notifier).refresh(),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            children: <Widget>[
              if (state.isStale) _StaleBanner(message: _staleMessage(state)),
              if (summary.needsReviewCount > 0)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                  child: _NeedsReviewBanner(count: summary.needsReviewCount),
                ),
              const SizedBox(height: 8),
              for (final ProjectDashboardCard card in summary.projects)
                ProjectCard(
                  card: card,
                  onTap: () {
                    // MT-5.6-01 → MT-5.6-02 handoff: preselect the
                    // project, then land on the Board tab. The selector
                    // state is the single source of truth the board and
                    // the SSE filter both watch.
                    ref
                        .read(currentProjectProvider.notifier)
                        .select(card.projectId);
                    ref.read(shellIndexProvider.notifier).select(1);
                  },
                ),
              const SizedBox(height: 16),
            ],
          ),
        );
    }
  }

  static String _staleMessage(DashboardState state) {
    final OrchestratorApiException? error = state.error;
    return error == null
        ? 'Offline — showing the last loaded overview.'
        : '${friendlyReadErrorMessage(error)} Showing the last loaded '
            'overview.';
  }
}

/// Section 14.2 offline state: cached overview, honestly marked stale and
/// never presented as live.
class _StaleBanner extends StatelessWidget {
  const _StaleBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      key: const ValueKey<String>('dashboard-stale-banner'),
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.cloud_off,
              size: 20, color: theme.colorScheme.onSecondaryContainer),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSecondaryContainer,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Section 14.1's "needs review" banner — driven by the summary's
/// `in_human_review` counts (FR-MOB-04's escalation visibility, passive
/// here; push/deep-link land in WP-5.4/5.9).
class _NeedsReviewBanner extends StatelessWidget {
  const _NeedsReviewBanner({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      key: const ValueKey<String>('needs-review-banner'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.rate_review_outlined,
              color: theme.colorScheme.onErrorContainer),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              '$count ${count == 1 ? 'task needs' : 'tasks need'} '
              'your review',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onErrorContainer,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Loading skeleton (Section 20.3: a distinct, honest loading state —
/// placeholder geometry, zero fake business data).
class _LoadingSkeleton extends StatelessWidget {
  const _LoadingSkeleton();

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        for (int i = 0; i < 3; i++)
          Container(
            key: ValueKey<String>('dashboard-skeleton-$i'),
            height: 120,
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest
                  .withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(12),
            ),
          ),
      ],
    );
  }
}

/// Empty state: the summary loaded but contains no projects
/// (Section 20.3).
class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(Icons.dashboard_outlined,
                size: 48, color: theme.colorScheme.outline),
            const SizedBox(height: 16),
            Text(
              'No projects yet.',
              style: theme.textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Create a project in the web app and it will appear here.',
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.outline),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

/// Error state (Section 20.3): friendly catalog-code copy, never the raw
/// server message (Section 12.4), with a retry affordance.
class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(Icons.cloud_off_outlined,
                size: 48, color: theme.colorScheme.outline),
            const SizedBox(height: 16),
            Text(
              message,
              style: theme.textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              key: const ValueKey<String>('dashboard-retry'),
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }
}
