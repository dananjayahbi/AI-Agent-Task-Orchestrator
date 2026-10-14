import 'package:built_value/serializer.dart' show FullType;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../app/routes.dart';
import '../../core/api/read_error_messages.dart';
import 'audit_log_providers.dart';

/// Audit log area (parent plan Section 14.1): a **read-only** list with
/// filters — MT-5.9-04 (FR-MOB-07).
///
/// * Read-only is structural: the repository behind this screen has no
///   mutating method, the feature issues only `GET /events`, and the
///   only row interaction is navigation to task detail (Section 12.5 /
///   FR-SEC-03 — the widget test asserts no mutating request is ever
///   recorded).
/// * Rows show the Section 12.5 essentials the **envelope** carries —
///   what changed (type), actor, ids, time. `correlation_id` is a
///   database column the Section 9.6 envelope deliberately never
///   carries ("exactly the seven keys"), so it is omitted here rather
///   than faked; wide `data` payloads are not dumped on a phone —
///   depth lives behind task detail (Sections 13.2-style progressive
///   disclosure).
/// * Filters map 1:1 to the API's documented query parameters
///   (`project`, `task`); actor/date/type are not accepted by
///   `GET /events`, so they are not offered (Section 18 Contract row).
class AuditLogScreen extends ConsumerStatefulWidget {
  const AuditLogScreen({super.key});

  @override
  ConsumerState<AuditLogScreen> createState() => _AuditLogScreenState();
}

class _AuditLogScreenState extends ConsumerState<AuditLogScreen> {
  final TextEditingController _projectController = TextEditingController();
  final TextEditingController _taskController = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Seed the fields from the active filter (chips round-trip).
    final AuditLogFilter filter = ref.read(auditLogProvider).filter;
    _projectController.text = filter.project ?? '';
    _taskController.text = filter.task ?? '';
  }

  @override
  void dispose() {
    _projectController.dispose();
    _taskController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final AuditLogState state = ref.watch(auditLogProvider);
    final ThemeData theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Audit log')),
      body: Column(
        children: <Widget>[
          // The filter bar stays visible in every state — a validation
          // message or a retry must never hide behind a spinner.
          _FilterBar(
            state: state,
            projectController: _projectController,
            taskController: _taskController,
          ),
          if (state.notice != null)
            Container(
              key: const ValueKey<String>('audit-notice'),
              margin: const EdgeInsets.fromLTRB(16, 4, 16, 0),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: theme.colorScheme.secondaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      state.notice!,
                      style: theme.textTheme.bodySmall,
                    ),
                  ),
                  IconButton(
                    key: const ValueKey<String>('audit-notice-dismiss'),
                    icon: const Icon(Icons.close, size: 16),
                    onPressed: () =>
                        ref.read(auditLogProvider.notifier).dismissNotice(),
                  ),
                ],
              ),
            ),
          Expanded(child: _body(state)),
        ],
      ),
    );
  }

  Widget _body(AuditLogState state) {
    switch (state.status) {
      case AuditLogStatus.loading:
        return const Center(
          key: ValueKey<String>('audit-loading'),
          child: CircularProgressIndicator(),
        );
      case AuditLogStatus.error:
        return _errorView(state);
      case AuditLogStatus.ready:
        return _readyView(state);
    }
  }

  Widget _errorView(AuditLogState state) {
    return Center(
      key: const ValueKey<String>('audit-error'),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Text(
              state.errorMessage ?? friendlyReadErrorMessage(state.error!),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              key: const ValueKey<String>('audit-retry'),
              onPressed: () => ref.read(auditLogProvider.notifier).load(),
              icon: const Icon(Icons.refresh),
              label: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _readyView(AuditLogState state) {
    final ThemeData theme = Theme.of(context);
    if (state.events.isEmpty) {
      return Center(
        key: ValueKey<String>(
          state.filter.isActive ? 'audit-empty-filters' : 'audit-empty',
        ),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            state.filter.isActive
                ? 'No events match these filters.'
                : 'No events recorded yet.',
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: theme.colorScheme.outline),
          ),
        ),
      );
    }
    return ListView.separated(
      key: const ValueKey<String>('audit-scroll'),
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      itemCount: state.visible.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (BuildContext context, int index) =>
          _EventRow(event: state.visible[index]),
    );
  }
}

/// The filter bar: the two API-supported filters with validation,
/// apply and clear, plus active chips with individual clear.
class _FilterBar extends ConsumerWidget {
  const _FilterBar({
    required this.state,
    required this.projectController,
    required this.taskController,
  });

  final AuditLogState state;
  final TextEditingController projectController;
  final TextEditingController taskController;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ThemeData theme = Theme.of(context);
    final AuditLogNotifier notifier = ref.read(auditLogProvider.notifier);
    return Container(
      key: const ValueKey<String>('audit-filter-bar'),
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: SizedBox(
                  height: 44,
                  child: TextField(
                    key: const ValueKey<String>('audit-filter-project'),
                    controller: projectController,
                    decoration: const InputDecoration(
                      isDense: true,
                      labelText: 'Project (PID00001)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: SizedBox(
                  height: 44,
                  child: TextField(
                    key: const ValueKey<String>('audit-filter-task'),
                    controller: taskController,
                    decoration: const InputDecoration(
                      isDense: true,
                      labelText: 'Task (PID00001-T001)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
              ),
            ],
          ),
          if (state.filterError != null)
            Padding(
              key: const ValueKey<String>('audit-filter-error'),
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                state.filterError!,
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.error),
              ),
            ),
          const SizedBox(height: 8),
          Row(
            children: <Widget>[
              FilledButton.tonal(
                key: const ValueKey<String>('audit-filter-apply'),
                onPressed: () => notifier.applyFilter(
                  project: projectController.text,
                  task: taskController.text,
                ),
                child: const Text('Apply filters'),
              ),
              const SizedBox(width: 8),
              TextButton(
                key: const ValueKey<String>('audit-filter-clear'),
                onPressed: () {
                  projectController.clear();
                  taskController.clear();
                  notifier.clearFilters();
                },
                child: const Text('Clear'),
              ),
            ],
          ),
          if (state.filter.isActive)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Wrap(
                spacing: 6,
                runSpacing: 4,
                children: <Widget>[
                  if (state.filter.project != null)
                    _FilterChip(
                      label: 'project: ${state.filter.project}',
                      onDeleted: () {
                        projectController.clear();
                        notifier.applyFilter(
                          project: '',
                          task: taskController.text,
                        );
                      },
                    ),
                  if (state.filter.task != null)
                    _FilterChip(
                      label: 'task: ${state.filter.task}',
                      onDeleted: () {
                        taskController.clear();
                        notifier.applyFilter(
                          project: projectController.text,
                          task: '',
                        );
                      },
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({required this.label, required this.onDeleted});

  final String label;
  final VoidCallback onDeleted;

  @override
  Widget build(BuildContext context) {
    return InputChip(
      label: Text(label),
      onDeleted: onDeleted,
    );
  }
}

/// One Section 12.5 essentials row: what changed, when, actor, ids.
class _EventRow extends StatelessWidget {
  const _EventRow({required this.event});

  final EventEnvelope event;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final String wireType = eventWireType(event.type);
    final String? taskId = event.taskId;
    return Container(
      key: ValueKey<String>('audit-row-${event.id}'),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                key: ValueKey<String>('audit-row-type-${event.id}'),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: theme.colorScheme.secondaryContainer,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(wireType, style: theme.textTheme.labelSmall),
              ),
              const Spacer(),
              Text(
                key: ValueKey<String>('audit-row-time-${event.id}'),
                formatEventTime(event.occurredAt),
                style: theme.textTheme.labelSmall
                    ?.copyWith(color: theme.colorScheme.outline),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            key: ValueKey<String>('audit-row-actor-${event.id}'),
            'actor: ${event.actor.type.name} · ${event.actor.ref}',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 2),
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  key: ValueKey<String>('audit-row-project-${event.id}'),
                  event.projectId,
                  style: theme.textTheme.labelSmall
                      ?.copyWith(fontFamily: 'monospace'),
                ),
              ),
              if (taskId != null && taskId.isNotEmpty)
                InkWell(
                  key: ValueKey<String>('audit-row-task-${event.id}'),
                  onTap: () => Navigator.pushNamed(
                    context,
                    AppArea.taskDetail.path,
                    arguments: taskId,
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 4,
                      vertical: 2,
                    ),
                    child: Text(
                      '$taskId ›',
                      style: theme.textTheme.labelSmall?.copyWith(
                        fontFamily: 'monospace',
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// The wire spelling of an event type (Section 9.6 catalog — the
/// generated enum's Dart name differs from the wire dot notation, and
/// the viewer shows the canonical catalog string, Section 20.5).
String eventWireType(EventEnvelopeTypeEnum type) {
  final Object? wire = serializers.serialize(
    type,
    specifiedType: const FullType(EventEnvelopeTypeEnum),
  );
  return wire is String ? wire : type.name;
}

/// Local-time rendering of the envelope's UTC instant (server clock in,
/// the Owner's clock out — Section 0.4). An unparsable timestamp shows
/// its raw value rather than a fabricated one.
String formatEventTime(String occurredAt) {
  final DateTime? parsed = DateTime.tryParse(occurredAt);
  if (parsed == null) {
    return occurredAt;
  }
  final DateTime local = parsed.toLocal();
  String two(int value) => value.toString().padLeft(2, '0');
  return '${two(local.year)}-${two(local.month)}-${two(local.day)} '
      '${two(local.hour)}:${two(local.minute)}';
}
