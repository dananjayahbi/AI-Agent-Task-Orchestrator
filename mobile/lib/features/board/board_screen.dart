import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../app/routes.dart';
import '../../core/api/read_error_messages.dart';
import '../../core/realtime/realtime_providers.dart';
import '../../core/realtime/sse_client.dart';
import '../../core/realtime/sse_connection_status.dart';
import 'board_providers.dart';
import 'board_states.dart';
import 'project_selector.dart';

/// Board area (parent plan Section 14.1): project selector, horizontally
/// paged state columns, pull to refresh, live updates — WP-5.6
/// (MT-5.6-02 selector + MT-5.6-03 paged board + MT-5.6-04/05 live).
///
/// * **Paging:** one page per canonical G-01 state in Section 8.1 order
///   ([boardStates]), swipe-paged with a tappable chip row as the page
///   indicator — touch is the primary interaction (FR-MOB-02).
/// * **Data:** one project-scoped fetch (MT-5.6-03 grouping decision),
///   grouped client-side by the canonical [StateEnum] — no hand-copied
///   state strings (G-01, NFR-11).
/// * **States:** each page renders its own loading / empty / error state
///   (Section 20.3) with errors mapped through the catalog-code friendly
///   copy (Section 20.4 item 5); a stale-from-cache board is banner-marked
///   offline and never presented as live (Section 14.2).
/// * **Liveness:** the AppBar chip reflects the shared MT-5.5-05 SSE
///   client's real connection status — polling fallback is labeled
///   honestly, never as "live" (Section 14.2, RISK-05).
class BoardScreen extends ConsumerStatefulWidget {
  const BoardScreen({super.key});

  @override
  ConsumerState<BoardScreen> createState() => _BoardScreenState();
}

class _BoardScreenState extends ConsumerState<BoardScreen> {
  final PageController _pageController = PageController();
  int _page = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _goToPage(int index) {
    if (index == _page) {
      return;
    }
    setState(() => _page = index);
    _pageController.animateToPage(
      index,
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    final BoardState state = ref.watch(boardProvider);
    final SseClient client = ref.watch(sseClientProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Board'),
        actions: <Widget>[
          // Honest liveness (MT-5.6-04): straight from the transport the
          // stream actually maintains — the UI never fakes "live".
          ValueListenableBuilder<SseConnectionStatus>(
            valueListenable: client.status,
            builder: (BuildContext context, SseConnectionStatus status, _) {
              return Center(
                child: Padding(
                  key: const ValueKey<String>('board-liveness'),
                  padding: const EdgeInsets.only(right: 12),
                  child: Tooltip(
                    message: boardLivenessLabel(status),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: _livenessColor(context, status),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        boardLivenessLabel(status),
                        key: const ValueKey<String>('board-liveness-label'),
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ],
      ),
      body: Column(
        children: <Widget>[
          const ProjectSelector(),
          Expanded(child: _body(state)),
        ],
      ),
    );
  }

  Widget _body(BoardState state) {
    if (state.projectId == null) {
      // Distinct from a page's empty state: no project is selected at all
      // (Section 20.3) — the selector above is where the user acts. Also
      // the honest first frame when the app opens with no selection (a
      // loading spinner for nothing would be a fake state).
      return Center(
        key: const ValueKey<String>('board-no-project'),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            'Select a project above to see its board.',
            textAlign: TextAlign.center,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: Theme.of(context).colorScheme.outline),
          ),
        ),
      );
    }

    final Map<StateEnum, List<Task>> grouped = groupTasksByState(state.tasks);
    return Column(
      children: <Widget>[
        if (state.isStale)
          Container(
            key: const ValueKey<String>('board-stale-banner'),
            margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.secondaryContainer,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: <Widget>[
                Icon(
                  Icons.cloud_off,
                  size: 20,
                  color: Theme.of(context).colorScheme.onSecondaryContainer,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    state.error == null
                        ? 'Offline — showing the last loaded board.'
                        : '${friendlyReadErrorMessage(state.error!)} '
                            'Showing the last loaded board.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSecondaryContainer,
                        ),
                  ),
                ),
              ],
            ),
          ),
        // Page indicator: touch targets over the six canonical pages,
        // labels in Section 8.1 order, live task counts per state. A Wrap
        // keeps every page reachable without horizontal scrolling — no
        // hidden touch target on a narrow phone.
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: Wrap(
            spacing: 8,
            runSpacing: 4,
            children: <Widget>[
              for (int i = 0; i < boardStates.length; i++)
                ChoiceChip(
                  key: ValueKey<String>('board-page-chip-$i'),
                  // Counts only with data in hand — a loading board
                  // never shows fake zeros (Section 20.3).
                  label: Text(
                    state.status == BoardStatus.ready
                        ? '${boardStateLabel(boardStates[i])} '
                            '${grouped[boardStates[i]]!.length}'
                        : boardStateLabel(boardStates[i]),
                  ),
                  selected: i == _page,
                  onSelected: (_) => _goToPage(i),
                ),
            ],
          ),
        ),
        Expanded(
          child: PageView.builder(
            key: const ValueKey<String>('board-pages'),
            controller: _pageController,
            itemCount: boardStates.length,
            onPageChanged: (int index) => setState(() => _page = index),
            itemBuilder: (BuildContext context, int index) {
              final StateEnum pageState = boardStates[index];
              return _StatePage(
                key: ValueKey<String>('board-page-${pageState.name}'),
                stateValue: pageState,
                board: state,
                tasks: grouped[pageState]!,
              );
            },
          ),
        ),
      ],
    );
  }

  static Color _livenessColor(
      BuildContext context, SseConnectionStatus status) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    switch (status) {
      case SseConnectionStatus.connected:
        return scheme.secondaryContainer;
      case SseConnectionStatus.connecting:
      case SseConnectionStatus.reconnecting:
        return scheme.tertiaryContainer;
      case SseConnectionStatus.polling:
        return scheme.surfaceContainerHighest;
      case SseConnectionStatus.disconnected:
        return scheme.errorContainer;
    }
  }
}

/// Honest liveness copy for [status] (MT-5.6-04): straight from the
/// transport the stream actually maintains. The polling fallback (Section
/// 14.2, RISK-05) is never labeled "live".
String boardLivenessLabel(SseConnectionStatus status) {
  switch (status) {
    case SseConnectionStatus.disconnected:
      return 'Live updates off';
    case SseConnectionStatus.connecting:
      return 'Connecting…';
    case SseConnectionStatus.connected:
      return 'Live';
    case SseConnectionStatus.reconnecting:
      return 'Reconnecting…';
    case SseConnectionStatus.polling:
      return 'Periodic updates';
  }
}

/// One canonical-state page: its own loading / empty / error presentation
/// (Section 20.3) over the shared board data, with pull to refresh
/// re-fetching the current project's board (Section 14.1).
class _StatePage extends StatelessWidget {
  const _StatePage({
    super.key,
    required this.stateValue,
    required this.board,
    required this.tasks,
  });

  final StateEnum stateValue;
  final BoardState board;
  final List<Task> tasks;

  @override
  Widget build(BuildContext context) {
    final String label = boardStateLabel(stateValue);
    switch (board.status) {
      case BoardStatus.loading:
        return Center(
          key: ValueKey<String>('board-page-loading-${stateValue.name}'),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const CircularProgressIndicator(),
              const SizedBox(height: 12),
              Text('Loading $label…'),
            ],
          ),
        );
      case BoardStatus.error:
        return _PageError(
          stateValue: stateValue,
          message: friendlyReadErrorMessage(board.error!),
        );
      case BoardStatus.ready:
        if (tasks.isEmpty) {
          return LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) =>
                RefreshIndicator(
              onRefresh: () => _reload(context),
              child: ListView(
                key: ValueKey<String>('board-page-empty-${stateValue.name}'),
                physics: const AlwaysScrollableScrollPhysics(),
                children: <Widget>[
                  SizedBox(
                    height: constraints.maxHeight > 240
                        ? constraints.maxHeight - 72
                        : constraints.maxHeight,
                    child: Center(
                      child: Text('No tasks in $label.'),
                    ),
                  ),
                ],
              ),
            ),
          );
        }
        return RefreshIndicator(
          onRefresh: () => _reload(context),
          child: ListView.builder(
            key: ValueKey<String>('board-page-list-${stateValue.name}'),
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: tasks.length + 1,
            itemBuilder: (BuildContext context, int index) {
              if (index == tasks.length) {
                // Padding so the last card clears the pull-to-refresh gap.
                return const SizedBox(height: 24);
              }
              return _TaskCard(task: tasks[index]);
            },
          ),
        );
    }
  }

  Future<void> _reload(BuildContext context) {
    final ProviderContainer container = ProviderScope.containerOf(
      context,
      listen: false,
    );
    return container.read(boardProvider.notifier).load();
  }
}

class _PageError extends StatelessWidget {
  const _PageError({required this.stateValue, required this.message});

  final StateEnum stateValue;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      key: ValueKey<String>('board-page-error-${stateValue.name}'),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(
              Icons.cloud_off_outlined,
              size: 48,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              key: ValueKey<String>('board-page-retry-${stateValue.name}'),
              onPressed: () {
                final ProviderContainer container = ProviderScope.containerOf(
                  context,
                  listen: false,
                );
                container.read(boardProvider.notifier).load();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }
}

/// One touch-optimized task card (Section 14.1 overview-level detail; full
/// detail is the WP-5.7 Task detail screen): id, title, priority,
/// worker/progress basics, and the Section 8.1 merge-pending badge — a
/// badge on the card, never a seventh page.
class _TaskCard extends StatelessWidget {
  const _TaskCard({required this.task});

  final Task task;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final bool mergePending = isMergePending(task);
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        key: ValueKey<String>('board-card-${task.id}'),
        borderRadius: BorderRadius.circular(12),
        // Route stub/handoff (MT-5.6-03 scope): the WP-5.7 screen owns
        // the content; the board only navigates with the task id.
        onTap: () => Navigator.pushNamed(
          context,
          AppArea.taskDetail.path,
          arguments: task.id,
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(
                    child: Text(task.title, style: theme.textTheme.titleMedium),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'P: ${task.priority.name}',
                    key: ValueKey<String>('board-card-priority-${task.id}'),
                    style: theme.textTheme.labelMedium,
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                '${task.id} · ${task.state.name}',
                key: ValueKey<String>('board-card-meta-${task.id}'),
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.outline),
              ),
              const SizedBox(height: 4),
              Text(
                'Worker: ${task.workerAgentId ?? 'unassigned'} · '
                'attempt ${task.attemptNumber}',
                key: ValueKey<String>('board-card-worker-${task.id}'),
                style: theme.textTheme.bodySmall,
              ),
              if (mergePending) ...<Widget>[
                const SizedBox(height: 8),
                Container(
                  key: const ValueKey<String>('merge-pending-badge'),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.tertiaryContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    mergePendingBadgeLabel,
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: theme.colorScheme.onTertiaryContainer,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
