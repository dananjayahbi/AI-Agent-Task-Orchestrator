//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/checkpoint_create_kind_enum.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'checkpoint_create.g.dart';

/// ``POST /tasks/{id}/checkpoints`` input (Section 10.5 tool contract).
///
/// Properties:
/// * [sessionId] - Lease-holding session id (G-18) — the fencing pair's identity half.
/// * [leaseGeneration] - Fencing generation from the claim response (Section 8.6; ADR-012); a stale value answers LEASE_EXPIRED.
/// * [message] - The agent's progress report text (Section 10.5 tool input).
/// * [percent] - Optional 0-100 completion hint (Section 7.2 bounds; out-of-range answers VALIDATION_ERROR).
/// * [tokenUsage] - Free JSON token accounting blob (Section 7.2) — no fixed schema is invented here (MT-1.8-01 risk note; an OQ would freeze one).
/// * [kind] - progress | liveness | system (Section 7.2); default progress — the extension-carrying kind (OQ-04 recorded reading).  * `progress` - progress * `liveness` - liveness * `system` - system
@BuiltValue()
abstract class CheckpointCreate
    implements Built<CheckpointCreate, CheckpointCreateBuilder> {
  /// Lease-holding session id (G-18) — the fencing pair's identity half.
  @BuiltValueField(wireName: r'session_id')
  String get sessionId;

  /// Fencing generation from the claim response (Section 8.6; ADR-012); a stale value answers LEASE_EXPIRED.
  @BuiltValueField(wireName: r'lease_generation')
  int get leaseGeneration;

  /// The agent's progress report text (Section 10.5 tool input).
  @BuiltValueField(wireName: r'message')
  String? get message;

  /// Optional 0-100 completion hint (Section 7.2 bounds; out-of-range answers VALIDATION_ERROR).
  @BuiltValueField(wireName: r'percent')
  int? get percent;

  /// Free JSON token accounting blob (Section 7.2) — no fixed schema is invented here (MT-1.8-01 risk note; an OQ would freeze one).
  @BuiltValueField(wireName: r'token_usage')
  JsonObject? get tokenUsage;

  /// progress | liveness | system (Section 7.2); default progress — the extension-carrying kind (OQ-04 recorded reading).  * `progress` - progress * `liveness` - liveness * `system` - system
  @BuiltValueField(wireName: r'kind')
  CheckpointCreateKindEnum? get kind;
  // enum kindEnum {  progress,  liveness,  system,  };

  CheckpointCreate._();

  factory CheckpointCreate([void updates(CheckpointCreateBuilder b)]) =
      _$CheckpointCreate;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(CheckpointCreateBuilder b) => b
    ..message = ''
    ..kind = CheckpointCreateKindEnum.progress;

  @BuiltValueSerializer(custom: true)
  static Serializer<CheckpointCreate> get serializer =>
      _$CheckpointCreateSerializer();
}

class _$CheckpointCreateSerializer
    implements PrimitiveSerializer<CheckpointCreate> {
  @override
  final Iterable<Type> types = const [CheckpointCreate, _$CheckpointCreate];

  @override
  final String wireName = r'CheckpointCreate';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    CheckpointCreate object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'session_id';
    yield serializers.serialize(
      object.sessionId,
      specifiedType: const FullType(String),
    );
    yield r'lease_generation';
    yield serializers.serialize(
      object.leaseGeneration,
      specifiedType: const FullType(int),
    );
    if (object.message != null) {
      yield r'message';
      yield serializers.serialize(
        object.message,
        specifiedType: const FullType(String),
      );
    }
    if (object.percent != null) {
      yield r'percent';
      yield serializers.serialize(
        object.percent,
        specifiedType: const FullType.nullable(int),
      );
    }
    if (object.tokenUsage != null) {
      yield r'token_usage';
      yield serializers.serialize(
        object.tokenUsage,
        specifiedType: const FullType.nullable(JsonObject),
      );
    }
    if (object.kind != null) {
      yield r'kind';
      yield serializers.serialize(
        object.kind,
        specifiedType: const FullType(CheckpointCreateKindEnum),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    CheckpointCreate object, {
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
    required CheckpointCreateBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'session_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.sessionId = valueDes;
          break;
        case r'lease_generation':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.leaseGeneration = valueDes;
          break;
        case r'message':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.message = valueDes;
          break;
        case r'percent':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.percent = valueDes;
          break;
        case r'token_usage':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(JsonObject),
          ) as JsonObject?;
          if (valueDes == null) continue;
          result.tokenUsage = valueDes;
          break;
        case r'kind':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(CheckpointCreateKindEnum),
          ) as CheckpointCreateKindEnum?;
          if (valueDes == null) continue;
          result.kind = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  CheckpointCreate deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = CheckpointCreateBuilder();
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
