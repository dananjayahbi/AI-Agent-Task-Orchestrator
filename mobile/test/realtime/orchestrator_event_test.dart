import 'package:flutter_test/flutter_test.dart';
import 'package:orchestrator_mobile/core/realtime/orchestrator_event.dart';

import 'realtime_test_support.dart';

void main() {
  group('OrchestratorEvent.tryParse', () {
    test('deserializes the exact Section 9.6 envelope fields', () {
      final OrchestratorEvent? event =
          OrchestratorEvent.tryParse(envelopeJson(id: 42));
      expect(event, isNotNull);
      expect(event!.id, 42);
      expect(event.type, 'task.transitioned');
      expect(event.projectId, 'PID00001');
      expect(event.taskId, 'T-00042');
      // The plan renders instants as UTC (`...Z`).
      expect(event.occurredAt.isUtc, isTrue);
      expect(
        event.occurredAt.toIso8601String(),
        '2026-10-11T12:45:02.000Z',
      );
      expect(event.actor.type, 'agent');
      expect(event.actor.ref, 'agent-1');
      expect(event.data, <String, dynamic>{'to': 'in_progress'});
    });

    test('keeps null project/task and null data as null', () {
      final OrchestratorEvent? event = OrchestratorEvent.tryParse(
        envelopeJson(id: 1, projectId: null, taskId: null, data: null),
      );
      expect(event!.projectId, isNull);
      expect(event.taskId, isNull);
      expect(event.data, isNull);
    });

    test('malformed envelopes return null (skipped, never crash)', () {
      // Missing id.
      expect(
        OrchestratorEvent.tryParse(<String, dynamic>{
          'type': 'x',
          'occurred_at': '2026-10-11T12:45:02Z',
          'actor': <String, dynamic>{'type': 'owner'},
        }),
        isNull,
      );
      // Negative id.
      expect(
        OrchestratorEvent.tryParse(
          envelopeJson(id: 0)
              .map((String k, Object? v) => MapEntry(k, k == 'id' ? -1 : v)),
        ),
        isNull,
      );
      // Empty type.
      expect(
        OrchestratorEvent.tryParse(
          envelopeJson(id: 1)
              .map((String k, Object? v) => MapEntry(k, k == 'type' ? '' : v)),
        ),
        isNull,
      );
      // Bad occurred_at.
      expect(
        OrchestratorEvent.tryParse(
          envelopeJson(id: 1).map((String k, Object? v) =>
              MapEntry(k, k == 'occurred_at' ? 'not-a-date' : v)),
        ),
        isNull,
      );
      // Actor without a type.
      expect(
        OrchestratorEvent.tryParse(
          envelopeJson(id: 1).map((String k, Object? v) =>
              MapEntry(k, k == 'actor' ? <String, dynamic>{'ref': 'x'} : v)),
        ),
        isNull,
      );
    });

    test('tryParseData skips invalid JSON without throwing', () {
      expect(OrchestratorEvent.tryParseData('not json'), isNull);
      expect(OrchestratorEvent.tryParseData('[1,2,3]'), isNull);
      expect(OrchestratorEvent.tryParseData('{"id":"x"}'), isNull);
    });

    test('tolerates unknown top-level keys (forward compatible)', () {
      final Map<String, dynamic> json = envelopeJson(id: 9);
      json['future_field'] = 'ignored';
      expect(OrchestratorEvent.tryParse(json)!.id, 9);
    });
  });
}
