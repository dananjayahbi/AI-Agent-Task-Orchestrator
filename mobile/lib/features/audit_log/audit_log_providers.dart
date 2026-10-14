import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/read_error_messages.dart';
import 'audit_log_repository.dart';

/// Section 20.3 states for the audit log screen.
enum AuditLogStatus { loading, ready, error }

/// The two filters the API actually supports (`GET /events`: `project`
/// and `task` — Section 9.6). Actor/date/type are offered by the web
/// filter design (MT-4.10-02) but **not** by the contract, so they are
/// omitted here rather than emulated with client-side post-filtering
/// (Section 18 Contract row).
class AuditLogFilter {
  const AuditLogFilter({this.project, this.task});

  final String? project;
  final String? task;

  bool get isActive => project != null || task != null;

  AuditLogFilter copyWith({String? project, String? task, bool clear = false}) {
    if (clear) {
      return const AuditLogFilter();
    }
    return AuditLogFilter(
      project: project ?? this.project,
      task: task ?? this.task,
    );
  }

  @override
  bool operator ==(Object other) =>
      other is AuditLogFilter && other.project == project && other.task == task;

  @override
  int get hashCode => Object.hash(project, task);
}

/// Client-side validation for the two canonical id shapes (Section 7.3)
/// — catching a typo before the request instead of surfacing a 400.
/// Returns null when [value] is empty (no filter) or the error copy.
String? validateProjectFilter(String value) {
  final String trimmed = value.trim();
  if (trimmed.isEmpty) {
    return null;
  }
  return RegExp(r'^PID[0-9]{5}$').hasMatch(trimmed)
      ? null
      : 'Project id looks like PID00001 (five digits).';
}

String? validateTaskFilter(String value) {
  final String trimmed = value.trim();
  if (trimmed.isEmpty) {
    return null;
  }
  return RegExp(r'^PID[0-9]{5}-T[0-9]{3,}$').hasMatch(trimmed)
      ? null
      : 'Task id looks like PID00001-T001 (three or more digits).';
}

class AuditLogState {
  const AuditLogState({
    required this.status,
    this.events = const <EventEnvelope>[],
    this.filter = const AuditLogFilter(),
    this.error,
    this.errorMessage,
    this.notice,
    this.filterError,
  });

  const AuditLogState.loading({AuditLogFilter filter = const AuditLogFilter()})
      : this(status: AuditLogStatus.loading, filter: filter);

  final AuditLogStatus status;

  /// Every loaded row in the endpoint's declared id-ascending order.
  final List<EventEnvelope> events;

  /// Newest first — the viewer's Section 14.1 "reverse-chronological"
  /// presentation (the ascending wire order is display-order input,
  /// never shown as-is; see the WP changelog decision).
  List<EventEnvelope> get visible => events.reversed.toList();

  final AuditLogFilter filter;
  final OrchestratorApiException? error;

  /// Overrides the catalog message for client-side situations that are
  /// not catalog codes (history bound exceeded).
  final String? errorMessage;

  /// Informational strip over ready data (failed refresh, etc.).
  final String? notice;

  /// Filter-field validation copy (no request was sent).
  final String? filterError;

  bool get isEmpty => status == AuditLogStatus.ready && events.isEmpty;

  AuditLogState _copyWith({
    AuditLogStatus? status,
    List<EventEnvelope>? events,
    AuditLogFilter? filter,
    OrchestratorApiException? error,
    bool clearError = false,
    String? errorMessage,
    bool clearErrorMessage = false,
    String? notice,
    bool clearNotice = false,
    String? filterError,
    bool clearFilterError = false,
  }) {
    return AuditLogState(
      status: status ?? this.status,
      events: events ?? this.events,
      filter: filter ?? this.filter,
      error: clearError ? null : (error ?? this.error),
      errorMessage:
          clearErrorMessage ? null : (errorMessage ?? this.errorMessage),
      notice: clearNotice ? null : (notice ?? this.notice),
      filterError: clearFilterError ? null : (filterError ?? this.filterError),
    );
  }

  AuditLogState asLoading(AuditLogFilter filter) => AuditLogState(
        status: AuditLogStatus.loading,
        events: events,
        filter: filter,
      );

  AuditLogState asReady(List<EventEnvelope> loaded, AuditLogFilter filter) =>
      AuditLogState(
        status: AuditLogStatus.ready,
        events: loaded,
        filter: filter,
      );

  AuditLogState asError(
    OrchestratorApiException exception, {
    String? message,
  }) =>
      AuditLogState(
        status: AuditLogStatus.error,
        events: events,
        filter: filter,
        error: exception,
        errorMessage: message,
      );

  AuditLogState withNotice(String message) =>
      _copyWith(notice: message, clearError: false);

  AuditLogState withFilterError(String message) =>
      _copyWith(filterError: message);

  AuditLogState withoutFilterError() => _copyWith(clearFilterError: true);

  AuditLogState withoutNotice() => _copyWith(clearNotice: true);
}

/// Audit log state holder (MT-5.9-04) — one notifier for the screen
/// (filter state lives here, so no family).
///
/// **Paging decision (recorded in the WP changelog):** `GET /events`
/// declares id-**ascending** order with a forward-only cursor, so the
/// only honest way to show the newest rows first is to follow the
/// cursor to the end (page_size 100, bounded like every other list in
/// the app) and present the accumulated history reversed. The bound is
/// an honest, actionable error ("narrow with a filter") — never a
/// silently truncated *oldest* page dressed up as the newest.
class AuditLogNotifier extends Notifier<AuditLogState> {
  /// Safety bound for the cursor walk (same rationale as the board and
  /// task-detail repositories): a runaway history surfaces as an
  /// honest error, never a hang or a wrong-ended list.
  static const int maxPages = 50;

  static const int pageSize = 100;

  /// Monotonic load token — a walk superseded by a filter change is
  /// dropped, never written over the newer state.
  int _loadToken = 0;

  @override
  AuditLogState build() {
    Future<void>.microtask(load);
    return const AuditLogState.loading();
  }

  Future<void> load() async {
    final AuditLogFilter filter = state.filter;
    final AuditLogState previous = state;
    final int token = ++_loadToken;
    try {
      final AuditLogRepository repository =
          ref.read(auditLogRepositoryProvider);
      final List<EventEnvelope> all = <EventEnvelope>[];
      String? cursor;
      int pages = 0;
      while (true) {
        final AuditLogPage page = await repository.fetchEvents(
          project: filter.project,
          task: filter.task,
          cursor: cursor,
          pageSize: pageSize,
        );
        if (token != _loadToken) {
          return; // Superseded — drop silently.
        }
        all.addAll(page.events);
        pages += 1;
        if (page.nextCursor == null) {
          break;
        }
        if (pages >= maxPages) {
          state = AuditLogState(
            status: AuditLogStatus.error,
            events: const <EventEnvelope>[],
            filter: filter,
            errorMessage: 'This history is larger than $maxPages pages of '
                '$pageSize events — narrow it with the project or task '
                'filter to load a slice.',
          );
          return;
        }
        cursor = page.nextCursor;
      }
      state = previous.status == AuditLogStatus.ready
          ? previous.asReady(all, filter)
          : AuditLogState(
              status: AuditLogStatus.ready,
              events: all,
              filter: filter,
            );
    } on OrchestratorApiException catch (error) {
      if (token != _loadToken) {
        return; // Superseded — drop silently.
      }
      // A failed refresh keeps the loaded rows (honest notice) —
      // never replacing a good list with a transient error.
      if (previous.status == AuditLogStatus.ready &&
          previous.events.isNotEmpty) {
        state = previous.withNotice(friendlyReadErrorMessage(error));
      } else {
        state = AuditLogState(
          status: AuditLogStatus.error,
          events: previous.events,
          filter: filter,
          error: error,
        );
      }
    }
  }

  /// Validates and applies both filters, then reloads (pagination
  /// resets by construction — one walk per filter set).
  void applyFilter({required String project, required String task}) {
    final String? projectError = validateProjectFilter(project);
    final String? taskError = validateTaskFilter(task);
    final String? invalid = projectError ?? taskError;
    if (invalid != null) {
      state = state.withFilterError(invalid);
      return; // No request for an invalid filter (Section 18 contract).
    }
    final String projectValue = project.trim();
    final String taskValue = task.trim();
    state = state.withoutFilterError().asLoading(AuditLogFilter(
          project: projectValue.isEmpty ? null : projectValue,
          task: taskValue.isEmpty ? null : taskValue,
        ));
    load();
  }

  void clearFilters() {
    state = state.withoutFilterError().asLoading(const AuditLogFilter());
    load();
  }

  void dismissNotice() {
    state = state.withoutNotice();
  }
}

final NotifierProvider<AuditLogNotifier, AuditLogState> auditLogProvider =
    NotifierProvider<AuditLogNotifier, AuditLogState>(AuditLogNotifier.new);
