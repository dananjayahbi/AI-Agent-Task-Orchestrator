//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/review_decision_record.dart';
import 'package:orchestrator_mobile/src/model/verdict_task_state.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'review_decision_response.g.dart';

/// The frozen review response — the record + post-transition identity.
///
/// Properties:
/// * [decision] - The recorded Section 7.2 row (all decisions are recorded, Section 11.5).
/// * [task] - Post-transition task identity — merge_status pending marks T15's merge-pending sub-status; state pending is T16's return.
@BuiltValue()
abstract class ReviewDecisionResponse
    implements Built<ReviewDecisionResponse, ReviewDecisionResponseBuilder> {
  /// The recorded Section 7.2 row (all decisions are recorded, Section 11.5).
  @BuiltValueField(wireName: r'decision')
  ReviewDecisionRecord get decision;

  /// Post-transition task identity — merge_status pending marks T15's merge-pending sub-status; state pending is T16's return.
  @BuiltValueField(wireName: r'task')
  VerdictTaskState get task;

  ReviewDecisionResponse._();

  factory ReviewDecisionResponse(
          [void updates(ReviewDecisionResponseBuilder b)]) =
      _$ReviewDecisionResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ReviewDecisionResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<ReviewDecisionResponse> get serializer =>
      _$ReviewDecisionResponseSerializer();
}

class _$ReviewDecisionResponseSerializer
    implements PrimitiveSerializer<ReviewDecisionResponse> {
  @override
  final Iterable<Type> types = const [
    ReviewDecisionResponse,
    _$ReviewDecisionResponse
  ];

  @override
  final String wireName = r'ReviewDecisionResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ReviewDecisionResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'decision';
    yield serializers.serialize(
      object.decision,
      specifiedType: const FullType(ReviewDecisionRecord),
    );
    yield r'task';
    yield serializers.serialize(
      object.task,
      specifiedType: const FullType(VerdictTaskState),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    ReviewDecisionResponse object, {
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
    required ReviewDecisionResponseBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'decision':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(ReviewDecisionRecord),
          ) as ReviewDecisionRecord;
          result.decision.replace(valueDes);
          break;
        case r'task':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(VerdictTaskState),
          ) as VerdictTaskState;
          result.task.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ReviewDecisionResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ReviewDecisionResponseBuilder();
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
