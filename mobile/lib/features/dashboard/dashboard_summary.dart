import 'package:built_value/serializer.dart';

import 'package:orchestrator_mobile/orchestrator_mobile.dart';

/// Dashboard summary as delivered by `GET /dashboard/summary`
/// (Section 9.2 Dashboard row; Section 14.1 Home / Overview contents;
/// FR-MOB-01).
///
/// **Contract note (MT-5.6-01 gap workaround):** the endpoint is listed in
/// the Section 9.2 catalog but no backend work package has built it yet and
/// the committed `schemas/openapi.yaml` snapshot has no `/dashboard/summary`
/// path — so no generated typed model exists (NFR-11). Following the
/// WP-5.5 precedent (`DioEventHistorySource` for `GET /events`), this
/// hand-authors the wire shape documented by Section 14.1's Home row:
/// per-project cards carrying counts per state, velocity and active agents.
/// When the backend endpoint lands, this model is the reconciliation point
/// (see the WP-5.6 changelog gap note).
///
/// Parsing is tolerant like the SSE envelope parser: a malformed project row
/// is skipped, unknown state keys are ignored, and absent numeric fields
/// default to 0 (recorded as follow-up OQs — a backend that omits velocity
/// or active agents is a backend gap, never a reason to assemble numbers
/// client-side from extra calls; MT-5.6-01 risk note).
class DashboardSummary {
  const DashboardSummary({required this.projects});

  final List<ProjectDashboardCard> projects;

  /// Tasks currently needing the Owner's attention across all projects —
  /// the Section 14.1 "needs review" banner signal, derived from the
  /// documented per-state `in_human_review` counts (no invented field).
  int get needsReviewCount => projects.fold(
        0,
        (int sum, ProjectDashboardCard card) =>
            sum + (card.stateCounts[StateEnum.inHumanReview] ?? 0),
      );

  /// Parses one summary payload; null when the top-level shape is wrong so
  /// the caller surfaces an honest error instead of an empty dashboard.
  static DashboardSummary? tryParse(Map<String, dynamic> json) {
    final Object? projects = json['projects'];
    if (projects is! List) {
      return null;
    }
    final List<ProjectDashboardCard> parsed = <ProjectDashboardCard>[];
    for (final Object? item in projects) {
      if (item is! Map) {
        continue;
      }
      final ProjectDashboardCard? card =
          ProjectDashboardCard.tryParse(Map<String, dynamic>.from(item));
      if (card != null) {
        parsed.add(card);
      }
    }
    return DashboardSummary(projects: parsed);
  }

  /// Wire rendering for the Section 14.2 read-only cache round-trip.
  Map<String, dynamic> toWire() => <String, dynamic>{
        'projects': <Map<String, dynamic>>[
          for (final ProjectDashboardCard card in projects) card.toWire(),
        ],
      };
}

/// One project's overview card (Section 14.1: counts per state, velocity,
/// active agents).
class ProjectDashboardCard {
  const ProjectDashboardCard({
    required this.projectId,
    required this.name,
    required this.stateCounts,
    required this.velocity,
    required this.activeAgents,
  });

  final String projectId;
  final String name;

  /// Counts keyed by the canonical G-01 states from the API types — never
  /// by hand-copied strings.
  final Map<StateEnum, int> stateCounts;

  /// Velocity exactly as delivered by the summary endpoint (Section 14.1 /
  /// FR-MOB-01). Never computed client-side (MT-5.6-01 out-of-scope).
  final int velocity;

  /// Active agent count as delivered by the summary endpoint.
  final int activeAgents;

  static ProjectDashboardCard? tryParse(Map<String, dynamic> json) {
    final Object? projectId = json['project_id'];
    final Object? name = json['name'];
    if (projectId is! String || projectId.isEmpty || name is! String) {
      return null;
    }
    final Map<StateEnum, int> counts = <StateEnum, int>{};
    final Object? countsRaw = json['state_counts'];
    if (countsRaw is Map) {
      countsRaw.forEach((Object? key, Object? value) {
        if (key is! String || value is! int) {
          return;
        }
        final StateEnum? state = _stateFromWire(key);
        if (state != null) {
          counts[state] = value;
        }
      });
    }
    return ProjectDashboardCard(
      projectId: projectId,
      name: name,
      stateCounts: counts,
      velocity: _nonNegativeInt(json['velocity']),
      activeAgents: _nonNegativeInt(json['active_agents']),
    );
  }

  Map<String, dynamic> toWire() => <String, dynamic>{
        'project_id': projectId,
        'name': name,
        'state_counts': <String, int>{
          for (final MapEntry<StateEnum, int> entry in stateCounts.entries)
            _wireFromState(entry.key): entry.value,
        },
        'velocity': velocity,
        'active_agents': activeAgents,
      };

  /// Wire string → canonical enum through the generated serializers
  /// (G-01: the schema owns the mapping, no hand-copied state strings).
  static StateEnum? _stateFromWire(String wire) {
    try {
      return standardSerializers.deserialize(
        wire,
        specifiedType: const FullType(StateEnum),
      ) as StateEnum;
    } catch (_) {
      return null;
    }
  }

  static String _wireFromState(StateEnum state) {
    return standardSerializers.serialize(
      state,
      specifiedType: const FullType(StateEnum),
    )! as String;
  }

  static int _nonNegativeInt(Object? value) =>
      value is int && value >= 0 ? value : 0;
}
