//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/event_envelope_type_enum.dart';
import 'package:orchestrator_mobile/src/model/event_actor.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'event_envelope.g.dart';

/// The Section 9.6 event envelope — exactly the seven documented keys.
///
/// Properties:
/// * [id] - Monotonic event id — the SSE event id (Section 9.6).
/// * [type] - One of the Section 9.6 catalog types (closed set).  * `project.created` - project.created * `project.updated` - project.updated * `task.created` - task.created * `task.updated` - task.updated * `task.transitioned` - task.transitioned * `task.claimed` - task.claimed * `task.released` - task.released * `task.checkpoint` - task.checkpoint * `task.lease_expiring` - task.lease_expiring * `task.lease_expired` - task.lease_expired * `attachment.processing` - attachment.processing * `attachment.ready` - attachment.ready * `attachment.failed` - attachment.failed * `audit.claimed` - audit.claimed * `audit.passed` - audit.passed * `audit.escalated` - audit.escalated * `review.requested` - review.requested * `review.decided` - review.decided * `merge.started` - merge.started * `merge.succeeded` - merge.succeeded * `merge.failed` - merge.failed * `agent.session_started` - agent.session_started * `agent.session_ended` - agent.session_ended * `system.alert` - system.alert
/// * [projectId]
/// * [taskId]
/// * [occurredAt] - UTC instant rendered as YYYY-MM-DDTHH:MM:SSZ (Section 9.6).
/// * [actor]
/// * [data]
@BuiltValue()
abstract class EventEnvelope
    implements Built<EventEnvelope, EventEnvelopeBuilder> {
  /// Monotonic event id — the SSE event id (Section 9.6).
  @BuiltValueField(wireName: r'id')
  int get id;

  /// One of the Section 9.6 catalog types (closed set).  * `project.created` - project.created * `project.updated` - project.updated * `task.created` - task.created * `task.updated` - task.updated * `task.transitioned` - task.transitioned * `task.claimed` - task.claimed * `task.released` - task.released * `task.checkpoint` - task.checkpoint * `task.lease_expiring` - task.lease_expiring * `task.lease_expired` - task.lease_expired * `attachment.processing` - attachment.processing * `attachment.ready` - attachment.ready * `attachment.failed` - attachment.failed * `audit.claimed` - audit.claimed * `audit.passed` - audit.passed * `audit.escalated` - audit.escalated * `review.requested` - review.requested * `review.decided` - review.decided * `merge.started` - merge.started * `merge.succeeded` - merge.succeeded * `merge.failed` - merge.failed * `agent.session_started` - agent.session_started * `agent.session_ended` - agent.session_ended * `system.alert` - system.alert
  @BuiltValueField(wireName: r'type')
  EventEnvelopeTypeEnum get type;
  // enum typeEnum {  project.created,  project.updated,  task.created,  task.updated,  task.transitioned,  task.claimed,  task.released,  task.checkpoint,  task.lease_expiring,  task.lease_expired,  attachment.processing,  attachment.ready,  attachment.failed,  audit.claimed,  audit.passed,  audit.escalated,  review.requested,  review.decided,  merge.started,  merge.succeeded,  merge.failed,  agent.session_started,  agent.session_ended,  system.alert,  };

  @BuiltValueField(wireName: r'project_id')
  String get projectId;

  @BuiltValueField(wireName: r'task_id')
  String? get taskId;

  /// UTC instant rendered as YYYY-MM-DDTHH:MM:SSZ (Section 9.6).
  @BuiltValueField(wireName: r'occurred_at')
  String get occurredAt;

  @BuiltValueField(wireName: r'actor')
  EventActor get actor;

  @BuiltValueField(wireName: r'data')
  JsonObject? get data;

  EventEnvelope._();

  factory EventEnvelope([void updates(EventEnvelopeBuilder b)]) =
      _$EventEnvelope;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(EventEnvelopeBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<EventEnvelope> get serializer =>
      _$EventEnvelopeSerializer();
}

class _$EventEnvelopeSerializer implements PrimitiveSerializer<EventEnvelope> {
  @override
  final Iterable<Type> types = const [EventEnvelope, _$EventEnvelope];

  @override
  final String wireName = r'EventEnvelope';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    EventEnvelope object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(int),
    );
    yield r'type';
    yield serializers.serialize(
      object.type,
      specifiedType: const FullType(EventEnvelopeTypeEnum),
    );
    yield r'project_id';
    yield serializers.serialize(
      object.projectId,
      specifiedType: const FullType(String),
    );
    yield r'task_id';
    yield object.taskId == null
        ? null
        : serializers.serialize(
            object.taskId,
            specifiedType: const FullType.nullable(String),
          );
    yield r'occurred_at';
    yield serializers.serialize(
      object.occurredAt,
      specifiedType: const FullType(String),
    );
    yield r'actor';
    yield serializers.serialize(
      object.actor,
      specifiedType: const FullType(EventActor),
    );
    yield r'data';
    yield object.data == null
        ? null
        : serializers.serialize(
            object.data,
            specifiedType: const FullType.nullable(JsonObject),
          );
  }

  @override
  Object serialize(
    Serializers serializers,
    EventEnvelope object, {
    FullType specifiedType = FullType.unspecified,
  }) {
    return _serializeProperties(serializers, object,
            specifiedType: specifiedType)
        .toList();
  }

  void _deserializeProperties(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
    required List<Object?> serializedList,
    required EventEnvelopeBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.id = valueDes;
          break;
        case r'type':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(EventEnvelopeTypeEnum),
          ) as EventEnvelopeTypeEnum;
          result.type = valueDes;
          break;
        case r'project_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.projectId = valueDes;
          break;
        case r'task_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.taskId = valueDes;
          break;
        case r'occurred_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.occurredAt = valueDes;
          break;
        case r'actor':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(EventActor),
          ) as EventActor;
          result.actor.replace(valueDes);
          break;
        case r'data':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(JsonObject),
          ) as JsonObject?;
          if (valueDes == null) continue;
          result.data = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  EventEnvelope deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = EventEnvelopeBuilder();
    final serializedList = (serialized as Iterable<Object?>).toList();
    final unhandled = <Object?>[];
    _deserializeProperties(
      serializers,
      serialized,
      specifiedType: specifiedType,
      serializedList: serializedList,
      unhandled: unhandled,
      result: result,
    );
    return result.build();
  }
}
