//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/decision_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'review_decision_request.g.dart';

/// ``POST /tasks/{id}/review`` input (Section 9.2 Review row).
///
/// Properties:
/// * [decision] - approve | request_changes | reassign — the only three the plan accepts; anything else is VALIDATION_ERROR (MT-3.6-01 risk note: never inferred from UI intent).  * `approve` - approve * `request_changes` - request_changes * `reassign` - reassign
/// * [note] - The reviewer's note — mandatory for request_changes (T16 guard), optional for reassign (it then becomes latest_feedback, Section 11.5), carried onto the approve record too.
/// * [resolutionId] - The resolution id the reviewer was looking at — **required for approve** (Section 14.2 approve safety; MT-3.6-04 binds the decision to it server-side and rejects an outdated id with VERSION_CONFLICT).
/// * [version] - The task ``version`` the client saw (FR-TSK-06) — a stale value answers VERSION_CONFLICT (409) and changes nothing.
@BuiltValue()
abstract class ReviewDecisionRequest
    implements Built<ReviewDecisionRequest, ReviewDecisionRequestBuilder> {
  /// approve | request_changes | reassign — the only three the plan accepts; anything else is VALIDATION_ERROR (MT-3.6-01 risk note: never inferred from UI intent).  * `approve` - approve * `request_changes` - request_changes * `reassign` - reassign
  @BuiltValueField(wireName: r'decision')
  DecisionEnum get decision;
  // enum decisionEnum {  approve,  request_changes,  reassign,  };

  /// The reviewer's note — mandatory for request_changes (T16 guard), optional for reassign (it then becomes latest_feedback, Section 11.5), carried onto the approve record too.
  @BuiltValueField(wireName: r'note')
  String? get note;

  /// The resolution id the reviewer was looking at — **required for approve** (Section 14.2 approve safety; MT-3.6-04 binds the decision to it server-side and rejects an outdated id with VERSION_CONFLICT).
  @BuiltValueField(wireName: r'resolution_id')
  String? get resolutionId;

  /// The task ``version`` the client saw (FR-TSK-06) — a stale value answers VERSION_CONFLICT (409) and changes nothing.
  @BuiltValueField(wireName: r'version')
  int get version;

  ReviewDecisionRequest._();

  factory ReviewDecisionRequest(
      [void updates(ReviewDecisionRequestBuilder b)]) = _$ReviewDecisionRequest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ReviewDecisionRequestBuilder b) => b..note = '';

  @BuiltValueSerializer(custom: true)
  static Serializer<ReviewDecisionRequest> get serializer =>
      _$ReviewDecisionRequestSerializer();
}

class _$ReviewDecisionRequestSerializer
    implements PrimitiveSerializer<ReviewDecisionRequest> {
  @override
  final Iterable<Type> types = const [
    ReviewDecisionRequest,
    _$ReviewDecisionRequest
  ];

  @override
  final String wireName = r'ReviewDecisionRequest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ReviewDecisionRequest object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'decision';
    yield serializers.serialize(
      object.decision,
      specifiedType: const FullType(DecisionEnum),
    );
    if (object.note != null) {
      yield r'note';
      yield serializers.serialize(
        object.note,
        specifiedType: const FullType(String),
      );
    }
    if (object.resolutionId != null) {
      yield r'resolution_id';
      yield serializers.serialize(
        object.resolutionId,
        specifiedType: const FullType.nullable(String),
      );
    }
    yield r'version';
    yield serializers.serialize(
      object.version,
      specifiedType: const FullType(int),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    ReviewDecisionRequest object, {
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
    required ReviewDecisionRequestBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'decision':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DecisionEnum),
          ) as DecisionEnum;
          result.decision = valueDes;
          break;
        case r'note':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.note = valueDes;
          break;
        case r'resolution_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.resolutionId = valueDes;
          break;
        case r'version':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
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
  ReviewDecisionRequest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ReviewDecisionRequestBuilder();
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
