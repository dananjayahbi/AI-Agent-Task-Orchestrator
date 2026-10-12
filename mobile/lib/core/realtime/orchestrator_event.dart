import 'dart:convert';

/// The Section 9.6 event actor as it appears on the wire:
/// `{"type": "...", "ref": "..."}` (Section 9.6 envelope example).
class EventActor {
  const EventActor({required this.type, this.ref});

  final String type;
  final String? ref;

  @override
  String toString() => 'EventActor($type, $ref)';
}

/// One typed Section 9.6 event envelope — the exact seven wire fields:
/// `id`, `type`, `project_id`, `task_id`, `occurred_at`, `actor`, `data`.
///
/// Hand-authored (transport-level model, MT-5.5-05 target path): the SSE
/// stream and the `GET /events` history endpoint declare their payload as a
/// binary/JSON stream in the contract, not as a generated REST model — the
/// typed *endpoint* client stays generated (NFR-11) while this wire shape
/// comes verbatim from Section 9.6 and `backend/apps/events/envelope.py`.
class OrchestratorEvent {
  const OrchestratorEvent({
    required this.id,
    required this.type,
    required this.projectId,
    required this.taskId,
    required this.occurredAt,
    required this.actor,
    required this.data,
  });

  /// Monotonic event id — the SSE `id:` value and the resume key
  /// (Section 9.6: "no gaps, no duplicates").
  final int id;

  /// Catalog event type, e.g. `task.transitioned` (Section 9.6 catalog).
  final String type;

  final String? projectId;
  final String? taskId;

  /// UTC instant from the plan's `2026-10-11T12:45:02Z` rendering.
  final DateTime occurredAt;

  final EventActor actor;

  /// Free-form event payload; never interpreted by the transport layer.
  final Map<String, dynamic>? data;

  /// Parses one envelope; returns null when the JSON is malformed so the
  /// caller can skip it with a warning — a bad event never crashes the
  /// stream (MT-5.5-05 acceptance item 1).
  static OrchestratorEvent? tryParse(Map<String, dynamic> json) {
    try {
      final Object? id = json['id'];
      final Object? type = json['type'];
      final Object? occurredAt = json['occurred_at'];
      if (id is! int || id < 0 || type is! String || type.isEmpty) {
        return null;
      }
      if (occurredAt is! String) {
        return null;
      }
      final DateTime? at = DateTime.tryParse(occurredAt);
      if (at == null) {
        return null;
      }
      final Object? actorRaw = json['actor'];
      final Map<String, dynamic> actorMap = actorRaw is Map
          ? Map<String, dynamic>.from(actorRaw)
          : const <String, dynamic>{};
      final Object? actorType = actorMap['type'];
      if (actorType is! String || actorType.isEmpty) {
        return null;
      }
      final Object? actorRef = actorMap['ref'];
      final Object? dataRaw = json['data'];
      return OrchestratorEvent(
        id: id,
        type: type,
        projectId: _optionalString(json['project_id']),
        taskId: _optionalString(json['task_id']),
        occurredAt: at.toUtc(),
        actor: EventActor(
          type: actorType,
          ref: actorRef is String ? actorRef : null,
        ),
        data: dataRaw is Map ? Map<String, dynamic>.from(dataRaw) : null,
      );
    } catch (_) {
      return null;
    }
  }

  /// Parses a JSON string (the SSE `data:` line); null when malformed.
  static OrchestratorEvent? tryParseData(String data) {
    try {
      final Object? decoded = jsonDecode(data);
      if (decoded is! Map) {
        return null;
      }
      return tryParse(Map<String, dynamic>.from(decoded));
    } catch (_) {
      return null;
    }
  }

  static String? _optionalString(Object? value) =>
      value is String && value.isNotEmpty ? value : null;

  @override
  String toString() => 'OrchestratorEvent($id, $type, $projectId, $taskId)';
}
