//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/role_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'claim_request.g.dart';

/// ``POST /tasks/{id}/claim`` input (Section 10.5 claim_task).
///
/// Properties:
/// * [sessionId] - Bridge-issued session id (G-18) — the lease's identity half.
/// * [workerAgentId] - Human-readable worker label (Section 7.2 worker_agent_id; self-declared and spoofable — a label only, G-18).
/// * [role] - Section 10.5 claim_task role input (coder default, auditor). Request intent only: the token's scopes gate first (Section 12.2) and the state decides inside the lock — coder claims only `pending` (T4), auditor only `to_be_audited` (T11) — a mismatch answers ROLE_NOT_PERMITTED (MT-3.3-01).  * `coder` - coder * `auditor` - auditor
@BuiltValue()
abstract class ClaimRequest
    implements Built<ClaimRequest, ClaimRequestBuilder> {
  /// Bridge-issued session id (G-18) — the lease's identity half.
  @BuiltValueField(wireName: r'session_id')
  String get sessionId;

  /// Human-readable worker label (Section 7.2 worker_agent_id; self-declared and spoofable — a label only, G-18).
  @BuiltValueField(wireName: r'worker_agent_id')
  String get workerAgentId;

  /// Section 10.5 claim_task role input (coder default, auditor). Request intent only: the token's scopes gate first (Section 12.2) and the state decides inside the lock — coder claims only `pending` (T4), auditor only `to_be_audited` (T11) — a mismatch answers ROLE_NOT_PERMITTED (MT-3.3-01).  * `coder` - coder * `auditor` - auditor
  @BuiltValueField(wireName: r'role')
  RoleEnum? get role;
  // enum roleEnum {  coder,  auditor,  };

  ClaimRequest._();

  factory ClaimRequest([void updates(ClaimRequestBuilder b)]) = _$ClaimRequest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ClaimRequestBuilder b) => b..role = RoleEnum.coder;

  @BuiltValueSerializer(custom: true)
  static Serializer<ClaimRequest> get serializer => _$ClaimRequestSerializer();
}

class _$ClaimRequestSerializer implements PrimitiveSerializer<ClaimRequest> {
  @override
  final Iterable<Type> types = const [ClaimRequest, _$ClaimRequest];

  @override
  final String wireName = r'ClaimRequest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ClaimRequest object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'session_id';
    yield serializers.serialize(
      object.sessionId,
      specifiedType: const FullType(String),
    );
    yield r'worker_agent_id';
    yield serializers.serialize(
      object.workerAgentId,
      specifiedType: const FullType(String),
    );
    if (object.role != null) {
      yield r'role';
      yield serializers.serialize(
        object.role,
        specifiedType: const FullType(RoleEnum),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    ClaimRequest object, {
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
    required ClaimRequestBuilder result,
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
        case r'worker_agent_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.workerAgentId = valueDes;
          break;
        case r'role':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(RoleEnum),
          ) as RoleEnum?;
          if (valueDes == null) continue;
          result.role = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ClaimRequest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ClaimRequestBuilder();
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
