//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/transport_enum.dart';
import 'package:orchestrator_mobile/src/model/capability_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'agent_session.g.dart';

/// The Section 7.2 Agent Session row as it goes over the wire.
///
/// Properties:
/// * [id]
/// * [projectId]
/// * [tokenId]
/// * [agentLabel]
/// * [clientName]
/// * [capability]
/// * [transport]
/// * [startedAt]
/// * [lastSeenAt]
/// * [endedAt]
@BuiltValue()
abstract class AgentSession
    implements Built<AgentSession, AgentSessionBuilder> {
  @BuiltValueField(wireName: r'id')
  String get id;

  @BuiltValueField(wireName: r'project_id')
  String get projectId;

  @BuiltValueField(wireName: r'token_id')
  int get tokenId;

  @BuiltValueField(wireName: r'agent_label')
  String get agentLabel;

  @BuiltValueField(wireName: r'client_name')
  String get clientName;

  @BuiltValueField(wireName: r'capability')
  CapabilityEnum get capability;
  // enum capabilityEnum {  vision,  text_only,  unknown,  };

  @BuiltValueField(wireName: r'transport')
  TransportEnum get transport;
  // enum transportEnum {  stdio,  http,  };

  @BuiltValueField(wireName: r'started_at')
  DateTime get startedAt;

  @BuiltValueField(wireName: r'last_seen_at')
  DateTime get lastSeenAt;

  @BuiltValueField(wireName: r'ended_at')
  DateTime? get endedAt;

  AgentSession._();

  factory AgentSession([void updates(AgentSessionBuilder b)]) = _$AgentSession;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AgentSessionBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AgentSession> get serializer => _$AgentSessionSerializer();
}

class _$AgentSessionSerializer implements PrimitiveSerializer<AgentSession> {
  @override
  final Iterable<Type> types = const [AgentSession, _$AgentSession];

  @override
  final String wireName = r'AgentSession';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AgentSession object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'project_id';
    yield serializers.serialize(
      object.projectId,
      specifiedType: const FullType(String),
    );
    yield r'token_id';
    yield serializers.serialize(
      object.tokenId,
      specifiedType: const FullType(int),
    );
    yield r'agent_label';
    yield serializers.serialize(
      object.agentLabel,
      specifiedType: const FullType(String),
    );
    yield r'client_name';
    yield serializers.serialize(
      object.clientName,
      specifiedType: const FullType(String),
    );
    yield r'capability';
    yield serializers.serialize(
      object.capability,
      specifiedType: const FullType(CapabilityEnum),
    );
    yield r'transport';
    yield serializers.serialize(
      object.transport,
      specifiedType: const FullType(TransportEnum),
    );
    yield r'started_at';
    yield serializers.serialize(
      object.startedAt,
      specifiedType: const FullType(DateTime),
    );
    yield r'last_seen_at';
    yield serializers.serialize(
      object.lastSeenAt,
      specifiedType: const FullType(DateTime),
    );
    yield r'ended_at';
    yield object.endedAt == null
        ? null
        : serializers.serialize(
            object.endedAt,
            specifiedType: const FullType.nullable(DateTime),
          );
  }

  @override
  Object serialize(
    Serializers serializers,
    AgentSession object, {
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
    required AgentSessionBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.id = valueDes;
          break;
        case r'project_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.projectId = valueDes;
          break;
        case r'token_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.tokenId = valueDes;
          break;
        case r'agent_label':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.agentLabel = valueDes;
          break;
        case r'client_name':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.clientName = valueDes;
          break;
        case r'capability':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(CapabilityEnum),
          ) as CapabilityEnum;
          result.capability = valueDes;
          break;
        case r'transport':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(TransportEnum),
          ) as TransportEnum;
          result.transport = valueDes;
          break;
        case r'started_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.startedAt = valueDes;
          break;
        case r'last_seen_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.lastSeenAt = valueDes;
          break;
        case r'ended_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.endedAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AgentSession deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AgentSessionBuilder();
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
