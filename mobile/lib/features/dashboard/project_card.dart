import 'package:flutter/material.dart';

import '../../../orchestrator_mobile.dart'
    hide DashboardSummary, ProjectDashboardCard;
import '../dashboard/dashboard_summary.dart';

/// One project's overview card (Section 14.1 Home / Overview: "Project
/// cards (counts per state, velocity, active agents)"; FR-MOB-01).
///
/// Tap hands the project off to the Board (MT-5.6-02 preselect) — the card
/// itself performs no navigation, so widget tests can assert the handoff
/// without a navigator (MT-5.6-01 scope: "wire the handoff, not the
/// board").
class ProjectCard extends StatelessWidget {
  const ProjectCard({super.key, required this.card, required this.onTap});

  final ProjectDashboardCard card;
  final VoidCallback onTap;

  /// Canonical six-state display order (G-01 / Section 8.1) — labels only,
  /// grouping and logic always use the [StateEnum] keys.
  static const List<StateEnum> _countOrder = <StateEnum>[
    StateEnum.draft,
    StateEnum.pending,
    StateEnum.inProgress,
    StateEnum.toBeAudited,
    StateEnum.inHumanReview,
    StateEnum.completed,
  ];

  /// Display label for a canonical state — presentation only; grouping
  /// always keys on the [StateEnum] value (G-01). [StateEnum] is a
  /// built_value `EnumClass`, so an if-chain (not an exhaustive switch)
  /// with an honest name fallback.
  static String labelFor(StateEnum state) {
    if (state == StateEnum.draft) {
      return 'Draft';
    }
    if (state == StateEnum.pending) {
      return 'Pending';
    }
    if (state == StateEnum.inProgress) {
      return 'In progress';
    }
    if (state == StateEnum.toBeAudited) {
      return 'To be audited';
    }
    if (state == StateEnum.inHumanReview) {
      return 'Human review';
    }
    if (state == StateEnum.completed) {
      return 'Completed';
    }
    return state.name;
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final int reviewCount = card.stateCounts[StateEnum.inHumanReview] ?? 0;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        key: ValueKey<String>('project-card-${card.projectId}'),
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(card.name, style: theme.textTheme.titleMedium),
                  ),
                  if (reviewCount > 0)
                    Chip(
                      key: const ValueKey<String>('needs-review-chip'),
                      visualDensity: VisualDensity.compact,
                      label: Text('$reviewCount to review'),
                      backgroundColor: theme.colorScheme.errorContainer,
                    ),
                ],
              ),
              const SizedBox(height: 8),
              // Counts per state: one small stat per canonical state, in
              // Section 8.1 order, zero counts included (honest totals).
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: <Widget>[
                  for (final StateEnum state in _countOrder)
                    _StateCount(
                      label: labelFor(state),
                      count: card.stateCounts[state] ?? 0,
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Velocity ${card.velocity} · ${card.activeAgents} active '
                '${card.activeAgents == 1 ? 'agent' : 'agents'}',
                style: theme.textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StateCount extends StatelessWidget {
  const _StateCount({required this.label, required this.count});

  final String label;
  final int count;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        '$label $count',
        key: ValueKey<String>('state-count-$label'),
        style: theme.textTheme.labelSmall,
      ),
    );
  }
}
