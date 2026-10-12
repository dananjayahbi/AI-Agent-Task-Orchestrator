//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'checkpoint.g.dart';

/// One stored checkpoint — the Section 7.2 field list, as returned.
///
/// Properties:
/// * [id] - Server-generated row identity (7.2).
/// * [taskId] - The addressed task (Section 7.2).
/// * [attemptNumber] - The coder claim attempt at write time (copied, never joined — MT-1.8-01 risk note).
/// * [sessionId] - Bridge-issued session id of the reporting agent (G-18).
/// * [timestamp] - Server clock at insertion (P7) — the feed's 'when'.
/// * [message]
/// * [percent] - 0-100 hint, or null when the caller omitted it (7.2).
/// * [tokenUsage] - Free JSON token accounting blob (Section 7.2).
/// * [kind] - progress | liveness | system (7.2).
@BuiltValue()
abstract class Checkpoint implements Built<Checkpoint, CheckpointBuilder> {
  /// Server-generated row identity (7.2).
  @BuiltValueField(wireName: r'id')
  String get id;

  /// The addressed task (Section 7.2).
  @BuiltValueField(wireName: r'task_id')
  String get taskId;

  /// The coder claim attempt at write time (copied, never joined — MT-1.8-01 risk note).
  @BuiltValueField(wireName: r'attempt_number')
  int get attemptNumber;

  /// Bridge-issued session id of the reporting agent (G-18).
  @BuiltValueField(wireName: r'session_id')
  String get sessionId;

  /// Server clock at insertion (P7) — the feed's 'when'.
  @BuiltValueField(wireName: r'timestamp')
  DateTime get timestamp;

  @BuiltValueField(wireName: r'message')
  String get message;

  /// 0-100 hint, or null when the caller omitted it (7.2).
  @BuiltValueField(wireName: r'percent')
  int? get percent;

  /// Free JSON token accounting blob (Section 7.2).
  @BuiltValueField(wireName: r'token_usage')
  JsonObject? get tokenUsage;

  /// progress | liveness | system (7.2).
  @BuiltValueField(wireName: r'kind')
  String get kind;

  Checkpoint._();

  factory Checkpoint([void updates(CheckpointBuilder b)]) = _$Checkpoint;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(CheckpointBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<Checkpoint> get serializer => _$CheckpointSerializer();
}

class _$CheckpointSerializer implements PrimitiveSerializer<Checkpoint> {
  @override
  final Iterable<Type> types = const [Checkpoint, _$Checkpoint];

  @override
  final String wireName = r'Checkpoint';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    Checkpoint object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'task_id';
    yield serializers.serialize(
      object.taskId,
      specifiedType: const FullType(String),
    );
    yield r'attempt_number';
    yield serializers.serialize(
      object.attemptNumber,
      specifiedType: const FullType(int),
    );
    yield r'session_id';
    yield serializers.serialize(
      object.sessionId,
      specifiedType: const FullType(String),
    );
    yield r'timestamp';
    yield serializers.serialize(
      object.timestamp,
      specifiedType: const FullType(DateTime),
    );
    yield r'message';
    yield serializers.serialize(
      object.message,
      specifiedType: const FullType(String),
    );
    yield r'percent';
    yield object.percent == null
        ? null
        : serializers.serialize(
            object.percent,
            specifiedType: const FullType.nullable(int),
          );
    yield r'token_usage';
    yield object.tokenUsage == null
        ? null
        : serializers.serialize(
            object.tokenUsage,
            specifiedType: const FullType.nullable(JsonObject),
          );
    yield r'kind';
    yield serializers.serialize(
      object.kind,
      specifiedType: const FullType(String),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    Checkpoint object, {
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
    required CheckpointBuilder result,
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
        case r'task_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.taskId = valueDes;
          break;
        case r'attempt_number':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.attemptNumber = valueDes;
          break;
        case r'session_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.sessionId = valueDes;
          break;
        case r'timestamp':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.timestamp = valueDes;
          break;
        case r'message':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
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
            specifiedType: const FullType(String),
          ) as String;
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
  Checkpoint deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = CheckpointBuilder();
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
