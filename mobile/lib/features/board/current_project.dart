import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/realtime/realtime_providers.dart';

/// Which project the Board displays (MT-5.6-02; Section 14.1 "Project
/// selector").
///
/// The selection is the **single source of truth** for the board data
/// fetch *and* the realtime subscription's project filter (Section 9.6) —
/// both consumers watch this provider, so they can never disagree.
///
/// Persistence decision (MT-5.6-02 risk note): session-local. A
/// persisted selection would be restored before the device proves
/// connectivity, inviting the offline rule violation the plan warns about
/// (Section 14.2); a fresh launch with no selection is honest.
class CurrentProjectNotifier extends Notifier<String?> {
  @override
  String? build() => null;

  /// Selects [projectId] (null clears the selection) and re-filters the
  /// SSE subscription to match (MT-5.6-04 acceptance: the subscription
  /// follows the selection).
  void select(String? projectId) {
    if (state == projectId) {
      return;
    }
    state = projectId;
    // The stream client is the shared MT-5.5-05 instance; a filter switch
    // reconnects with Last-Event-ID so no event is lost or duplicated
    // across the change (Section 9.6 no-gaps/no-duplicates).
    ref.read(sseClientProvider).updateProjectFilter(projectId);
  }
}

/// The currently selected project id, or null when none is selected.
final NotifierProvider<CurrentProjectNotifier, String?> currentProjectProvider =
    NotifierProvider<CurrentProjectNotifier, String?>(
  CurrentProjectNotifier.new,
);
