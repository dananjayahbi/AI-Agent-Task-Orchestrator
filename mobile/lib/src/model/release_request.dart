//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'release_request.g.dart';

/// ``POST /tasks/{id}/release`` input (ADR-012 fencing carrier).
///
/// Properties:
/// * [sessionId] - Lease-holding session id — required for agent callers; omitted for the Owner override.
/// * [leaseGeneration] - Fencing generation from the claim response (Section 8.6) — required for agent callers; a stale value answers LEASE_EXPIRED.
/// * [reason] - Free-text reason recorded on the T6 Transition row's note (Section 10.5 release_task input).
/// * [version] - Optional FR-TSK-06 optimistic check: when present, a stale value answers VERSION_CONFLICT.
@BuiltValue()
abstract class ReleaseRequest
    implements Built<ReleaseRequest, ReleaseRequestBuilder> {
  /// Lease-holding session id — required for agent callers; omitted for the Owner override.
  @BuiltValueField(wireName: r'session_id')
  String? get sessionId;

  /// Fencing generation from the claim response (Section 8.6) — required for agent callers; a stale value answers LEASE_EXPIRED.
  @BuiltValueField(wireName: r'lease_generation')
  int? get leaseGeneration;

  /// Free-text reason recorded on the T6 Transition row's note (Section 10.5 release_task input).
  @BuiltValueField(wireName: r'reason')
  String? get reason;

  /// Optional FR-TSK-06 optimistic check: when present, a stale value answers VERSION_CONFLICT.
  @BuiltValueField(wireName: r'version')
  int? get version;

  ReleaseRequest._();

  factory ReleaseRequest([void updates(ReleaseRequestBuilder b)]) =
      _$ReleaseRequest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ReleaseRequestBuilder b) => b..reason = '';

  @BuiltValueSerializer(custom: true)
  static Serializer<ReleaseRequest> get serializer =>
      _$ReleaseRequestSerializer();
}

class _$ReleaseRequestSerializer
    implements PrimitiveSerializer<ReleaseRequest> {
  @override
  final Iterable<Type> types = const [ReleaseRequest, _$ReleaseRequest];

  @override
  final String wireName = r'ReleaseRequest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ReleaseRequest object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    if (object.sessionId != null) {
      yield r'session_id';
      yield serializers.serialize(
        object.sessionId,
        specifiedType: const FullType.nullable(String),
      );
    }
    if (object.leaseGeneration != null) {
      yield r'lease_generation';
      yield serializers.serialize(
        object.leaseGeneration,
        specifiedType: const FullType.nullable(int),
      );
    }
    if (object.reason != null) {
      yield r'reason';
      yield serializers.serialize(
        object.reason,
        specifiedType: const FullType(String),
      );
    }
    if (object.version != null) {
      yield r'version';
      yield serializers.serialize(
        object.version,
        specifiedType: const FullType.nullable(int),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    ReleaseRequest object, {
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
    required ReleaseRequestBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'session_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.sessionId = valueDes;
          break;
        case r'lease_generation':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.leaseGeneration = valueDes;
          break;
        case r'reason':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.reason = valueDes;
          break;
        case r'version':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.version = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ReleaseRequest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ReleaseRequestBuilder();
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
