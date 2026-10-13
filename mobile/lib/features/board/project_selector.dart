import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/read_error_messages.dart';
import 'current_project.dart';
import 'projects_providers.dart';

/// The MT-5.6-02 project selector (Section 14.1 Board row: "Project
/// selector"): a touch-friendly dropdown over `GET /projects`, showing
/// name + id + status where the payload provides it.
///
/// Selection state ([currentProjectProvider]) is the single source of
/// truth: the board data fetch and the SSE subscription's project filter
/// both watch it (Section 9.6). Empty (no projects) and error states are
/// distinct per Section 20.3 with catalog-code friendly copy.
class ProjectSelector extends ConsumerWidget {
  const ProjectSelector({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ProjectsState state = ref.watch(projectsProvider);
    final String? selectedId = ref.watch(currentProjectProvider);
    switch (state.status) {
      case ProjectsStatus.loading:
        return const Padding(
          key: ValueKey<String>('project-selector-loading'),
          padding: EdgeInsets.all(16),
          child: LinearProgressIndicator(),
        );
      case ProjectsStatus.error:
        return _SelectorError(
          message: friendlyReadErrorMessage(state.error!),
          onRetry: () => ref.read(projectsProvider.notifier).refresh(),
        );
      case ProjectsStatus.ready:
        final List<Project> projects = state.projects!;
        if (projects.isEmpty) {
          return const _SelectorEmpty();
        }
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: DropdownButtonFormField<String>(
            key: const ValueKey<String>('project-selector'),
            initialValue: selectedId,
            // The selector is always visible, even for a single project
            // (recorded MT-5.6-02 decision) — consistent affordance.
            decoration: const InputDecoration(
              labelText: 'Project',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            items: <DropdownMenuItem<String>>[
              for (final Project project in projects)
                DropdownMenuItem<String>(
                  value: project.id,
                  child: Text(
                    key: ValueKey<String>('project-option-${project.id}'),
                    _labelFor(project),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
            onChanged: (String? projectId) {
              // Single source of truth: selecting here refetches the
              // board and re-filters the stream (both watch the provider).
              ref.read(currentProjectProvider.notifier).select(projectId);
            },
          ),
        );
    }
  }

  static String _labelFor(Project project) {
    // [ActiveStatusEnum] is a built_value `EnumClass` — if-chain, not an
    // exhaustive switch.
    String status;
    if (project.activeStatus == ActiveStatusEnum.active) {
      status = 'active';
    } else if (project.activeStatus == ActiveStatusEnum.paused) {
      status = 'paused';
    } else {
      status = 'archived';
    }
    return '${project.name} (${project.id}, $status)';
  }
}

class _SelectorEmpty extends StatelessWidget {
  const _SelectorEmpty();

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Padding(
      key: const ValueKey<String>('project-selector-empty'),
      padding: const EdgeInsets.all(16),
      child: Text(
        'No projects yet — create one in the web app, then pull to '
        'refresh.',
        style: theme.textTheme.bodyMedium
            ?.copyWith(color: theme.colorScheme.outline),
      ),
    );
  }
}

class _SelectorError extends StatelessWidget {
  const _SelectorError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Padding(
      key: const ValueKey<String>('project-selector-error'),
      padding: const EdgeInsets.all(16),
      child: Row(
        children: <Widget>[
          Icon(Icons.error_outline, color: theme.colorScheme.error),
          const SizedBox(width: 12),
          Expanded(
            child: Text(message, style: theme.textTheme.bodyMedium),
          ),
          TextButton(
            onPressed: onRetry,
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }
}
