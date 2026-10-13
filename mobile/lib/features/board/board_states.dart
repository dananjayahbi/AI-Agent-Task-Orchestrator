import 'package:orchestrator_mobile/orchestrator_mobile.dart';

/// Canonical board states (MT-5.6-03; parent plan G-01 / Section 8.1).
///
/// The six canonical machine values live in the generated API types
/// ([StateEnum]). This module owns only their **board order** (the Section
/// 8.1 diagram order) and their **display labels** — labels are
/// presentation-only and never used for grouping (G-01 discipline).
///
/// Drift guard (mirrors the web board's compile-time coverage check,
/// MT-4.3-01): [boardStatesCoverageGuard] fails loudly in tests if the
/// schema grows a seventh state — a schema change must be a caught test
/// failure here, never a silent mis-grouping.
const List<StateEnum> boardStates = <StateEnum>[
  StateEnum.draft,
  StateEnum.pending,
  StateEnum.inProgress,
  StateEnum.toBeAudited,
  StateEnum.inHumanReview,
  StateEnum.completed,
];

/// Human labels — presentation only (G-01: machine values drive logic).
///
/// [StateEnum] is a built_value `EnumClass`, not a Dart enum, so a switch
/// expression over it can never be exhaustive — an if-chain over the six
/// canonical values with an honest name fallback is the correct shape.
String boardStateLabel(StateEnum state) {
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

/// True when [value] is one of the six canonical board states.
bool isBoardState(StateEnum value) => boardStates.contains(value);

/// Coverage guard: every [StateEnum] member must be listed in
/// [boardStates]. Returns the schema values that the board would silently
/// drop — tests assert this is empty (MT-5.6-03 risk note: page order and
/// labels stay identical to the web board's canonical order).
List<StateEnum> boardStatesCoverageGap() =>
    StateEnum.values.where((StateEnum v) => !isBoardState(v)).toList();

/// Groups tasks into one bucket per canonical state, keyed by the machine
/// value, preserving the server's FR-TSK-05 order within each page. A task
/// whose state is not one of the six cannot exist (contract enum);
/// defensively it is dropped rather than rendered under a wrong label.
Map<StateEnum, List<Task>> groupTasksByState(List<Task> tasks) {
  final Map<StateEnum, List<Task>> grouped = <StateEnum, List<Task>>{
    for (final StateEnum state in boardStates) state: <Task>[],
  };
  for (final Task task in tasks) {
    grouped[task.state]?.add(task);
  }
  return grouped;
}

/// Section 8.1's merge-pending sub-status: `merge_status = pending` is a
/// **badge on the card, never a seventh page** — the card stays in
/// `to_be_audited` or `in_human_review` until the Merge Executor reports.
bool isMergePending(Task task) => task.mergeStatus == 'pending';

/// "Approved, merging" badge text from the Section 8.1 note.
const String mergePendingBadgeLabel = 'Approved, merging';
