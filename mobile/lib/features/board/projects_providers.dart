import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import 'current_project.dart';
import 'projects_repository.dart';

/// Screen state of the Board's project selector (MT-5.6-02;
/// Section 20.3: empty and error are distinct states).
enum ProjectsStatus { loading, ready, error }

class ProjectsState {
  const ProjectsState({required this.status, this.projects, this.error});

  final ProjectsStatus status;
  final List<Project>? projects;
  final OrchestratorApiException? error;

  bool get isEmpty =>
      status == ProjectsStatus.ready && (projects?.isEmpty ?? true);
}

/// Loads the owner's projects for the selector and auto-selects when the
/// list makes the choice unambiguous.
///
/// Single-project behavior (MT-5.6-02 acceptance, recorded decision): the
/// selector stays visible in all cases — with one project it simply shows
/// that project. An auto-selection happens for the single-project case and
/// for a freshly loaded list with no valid current selection, so the board
/// is never silently blank behind a populated selector; user choice always
/// wins afterwards.
class ProjectsNotifier extends Notifier<ProjectsState> {
  @override
  ProjectsState build() {
    Future<void>.microtask(refresh);
    return const ProjectsState(status: ProjectsStatus.loading);
  }

  Future<void> refresh() async {
    try {
      final List<Project> projects =
          await ref.read(projectsRepositoryProvider).fetchAll();
      state = ProjectsState(status: ProjectsStatus.ready, projects: projects);
      _applyDefaultSelection(projects);
    } on OrchestratorApiException catch (error) {
      state = ProjectsState(status: ProjectsStatus.error, error: error);
    }
  }

  void _applyDefaultSelection(List<Project> projects) {
    final CurrentProjectNotifier selection =
        ref.read(currentProjectProvider.notifier);
    final String? current = ref.read(currentProjectProvider);
    final bool currentStillValid =
        current != null && projects.any((Project p) => p.id == current);
    if (currentStillValid) {
      return;
    }
    if (projects.length == 1) {
      // Single project: auto-select it (selector stays visible).
      selection.select(projects.first.id);
    } else {
      // Zero projects, or a stale selection that no longer resolves, or
      // several projects with no choice yet: selection is null and the
      // board shows its honest "pick a project" state — the UI never
      // picks for the user or keeps a ghost project (no-op when already
      // null).
      selection.select(null);
    }
  }
}

final NotifierProvider<ProjectsNotifier, ProjectsState> projectsProvider =
    NotifierProvider<ProjectsNotifier, ProjectsState>(ProjectsNotifier.new);
