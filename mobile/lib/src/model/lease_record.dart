//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'lease_record.g.dart';

/// The Section 8.6 lease JSON — the stored claim record, as documented.
///
/// Properties:
/// * [taskId]
/// * [assignedAgent]
/// * [sessionId]
/// * [role]
/// * [leaseGeneration]
/// * [leaseAcquiredAt]
/// * [leaseExpiresAt]
/// * [leaseHardCapAt]
/// * [lastCheckpoint]
/// * [failureRetryCount]
@BuiltValue()
abstract class LeaseRecord implements Built<LeaseRecord, LeaseRecordBuilder> {
  @BuiltValueField(wireName: r'task_id')
  String get taskId;

  @BuiltValueField(wireName: r'assigned_agent')
  String get assignedAgent;

  @BuiltValueField(wireName: r'session_id')
  String get sessionId;

  @BuiltValueField(wireName: r'role')
  String get role;

  @BuiltValueField(wireName: r'lease_generation')
  int get leaseGeneration;

  @BuiltValueField(wireName: r'lease_acquired_at')
  DateTime? get leaseAcquiredAt;

  @BuiltValueField(wireName: r'lease_expires_at')
  DateTime? get leaseExpiresAt;

  @BuiltValueField(wireName: r'lease_hard_cap_at')
  DateTime? get leaseHardCapAt;

  @BuiltValueField(wireName: r'last_checkpoint')
  DateTime? get lastCheckpoint;

  @BuiltValueField(wireName: r'failure_retry_count')
  int get failureRetryCount;

  LeaseRecord._();

  factory LeaseRecord([void updates(LeaseRecordBuilder b)]) = _$LeaseRecord;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(LeaseRecordBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<LeaseRecord> get serializer => _$LeaseRecordSerializer();
}

class _$LeaseRecordSerializer implements PrimitiveSerializer<LeaseRecord> {
  @override
  final Iterable<Type> types = const [LeaseRecord, _$LeaseRecord];

  @override
  final String wireName = r'LeaseRecord';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    LeaseRecord object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'task_id';
    yield serializers.serialize(
      object.taskId,
      specifiedType: const FullType(String),
    );
    yield r'assigned_agent';
    yield serializers.serialize(
      object.assignedAgent,
      specifiedType: const FullType(String),
    );
    yield r'session_id';
    yield serializers.serialize(
      object.sessionId,
      specifiedType: const FullType(String),
    );
    yield r'role';
    yield serializers.serialize(
      object.role,
      specifiedType: const FullType(String),
    );
    yield r'lease_generation';
    yield serializers.serialize(
      object.leaseGeneration,
      specifiedType: const FullType(int),
    );
    yield r'lease_acquired_at';
    yield object.leaseAcquiredAt == null
        ? null
        : serializers.serialize(
            object.leaseAcquiredAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'lease_expires_at';
    yield object.leaseExpiresAt == null
        ? null
        : serializers.serialize(
            object.leaseExpiresAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'lease_hard_cap_at';
    yield object.leaseHardCapAt == null
        ? null
        : serializers.serialize(
            object.leaseHardCapAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'last_checkpoint';
    yield object.lastCheckpoint == null
        ? null
        : serializers.serialize(
            object.lastCheckpoint,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'failure_retry_count';
    yield serializers.serialize(
      object.failureRetryCount,
      specifiedType: const FullType(int),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    LeaseRecord object, {
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
    required LeaseRecordBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'task_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.taskId = valueDes;
          break;
        case r'assigned_agent':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.assignedAgent = valueDes;
          break;
        case r'session_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.sessionId = valueDes;
          break;
        case r'role':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.role = valueDes;
          break;
        case r'lease_generation':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.leaseGeneration = valueDes;
          break;
        case r'lease_acquired_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.leaseAcquiredAt = valueDes;
          break;
        case r'lease_expires_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.leaseExpiresAt = valueDes;
          break;
        case r'lease_hard_cap_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.leaseHardCapAt = valueDes;
          break;
        case r'last_checkpoint':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.lastCheckpoint = valueDes;
          break;
        case r'failure_retry_count':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.failureRetryCount = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  LeaseRecord deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = LeaseRecordBuilder();
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
