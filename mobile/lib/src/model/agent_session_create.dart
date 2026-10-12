//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/transport_enum.dart';
import 'package:orchestrator_mobile/src/model/capability_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'agent_session_create.g.dart';

/// ``POST /agent-sessions`` input — no project field exists here (ADR-004).
///
/// Properties:
/// * [id]
/// * [agentLabel]
/// * [clientName]
/// * [capability]
/// * [transport]
@BuiltValue()
abstract class AgentSessionCreate
    implements Built<AgentSessionCreate, AgentSessionCreateBuilder> {
  @BuiltValueField(wireName: r'id')
  String get id;

  @BuiltValueField(wireName: r'agent_label')
  String? get agentLabel;

  @BuiltValueField(wireName: r'client_name')
  String? get clientName;

  @BuiltValueField(wireName: r'capability')
  CapabilityEnum? get capability;
  // enum capabilityEnum {  vision,  text_only,  unknown,  };

  @BuiltValueField(wireName: r'transport')
  TransportEnum get transport;
  // enum transportEnum {  stdio,  http,  };

  AgentSessionCreate._();

  factory AgentSessionCreate([void updates(AgentSessionCreateBuilder b)]) =
      _$AgentSessionCreate;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AgentSessionCreateBuilder b) => b
    ..agentLabel = ''
    ..clientName = ''
    ..capability = CapabilityEnum.unknown;

  @BuiltValueSerializer(custom: true)
  static Serializer<AgentSessionCreate> get serializer =>
      _$AgentSessionCreateSerializer();
}

class _$AgentSessionCreateSerializer
    implements PrimitiveSerializer<AgentSessionCreate> {
  @override
  final Iterable<Type> types = const [AgentSessionCreate, _$AgentSessionCreate];

  @override
  final String wireName = r'AgentSessionCreate';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AgentSessionCreate object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    if (object.agentLabel != null) {
      yield r'agent_label';
      yield serializers.serialize(
        object.agentLabel,
        specifiedType: const FullType(String),
      );
    }
    if (object.clientName != null) {
      yield r'client_name';
      yield serializers.serialize(
        object.clientName,
        specifiedType: const FullType(String),
      );
    }
    if (object.capability != null) {
      yield r'capability';
      yield serializers.serialize(
        object.capability,
        specifiedType: const FullType(CapabilityEnum),
      );
    }
    yield r'transport';
    yield serializers.serialize(
      object.transport,
      specifiedType: const FullType(TransportEnum),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    AgentSessionCreate object, {
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
    required AgentSessionCreateBuilder result,
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
        case r'agent_label':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.agentLabel = valueDes;
          break;
        case r'client_name':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.clientName = valueDes;
          break;
        case r'capability':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(CapabilityEnum),
          ) as CapabilityEnum?;
          if (valueDes == null) continue;
          result.capability = valueDes;
          break;
        case r'transport':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(TransportEnum),
          ) as TransportEnum;
          result.transport = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AgentSessionCreate deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AgentSessionCreateBuilder();
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
