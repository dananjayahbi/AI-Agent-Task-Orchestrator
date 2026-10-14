//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/decided_via_enum.dart';
import 'package:orchestrator_mobile/src/model/decision_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'review_decision_record.g.dart';

/// One recorded Section 7.2 Review Decision row, field for field.
///
/// Properties:
/// * [id] - Server-generated UUID (MT-3.6-02).
/// * [taskId] - Section 7.2 ``task_id``.
/// * [resolutionId] - Section 7.2 ``resolution_id`` — the current attempt's resolution the reviewer saw (mandatory for approve, MT-3.6-04; null for note actions on a review that never had a submission, e.g. T9).
/// * [decision] - approve | request_changes | reassign (Section 9.2's three).  * `approve` - approve * `request_changes` - request_changes * `reassign` - reassign
/// * [note] - The reviewer's note — mandatory for request_changes (T16 guard); it becomes the Task's latest_feedback (Section 11.5).
/// * [decidedBy] - The acting principal: owner user id (web) or device id (mobile).
/// * [decidedVia] - web | mobile — Section 7.2's two review channels (13/14).  * `web` - web * `mobile` - mobile
/// * [decidedAt] - Server clock at insertion (P7).
@BuiltValue()
abstract class ReviewDecisionRecord
    implements Built<ReviewDecisionRecord, ReviewDecisionRecordBuilder> {
  /// Server-generated UUID (MT-3.6-02).
  @BuiltValueField(wireName: r'id')
  String get id;

  /// Section 7.2 ``task_id``.
  @BuiltValueField(wireName: r'task_id')
  String get taskId;

  /// Section 7.2 ``resolution_id`` — the current attempt's resolution the reviewer saw (mandatory for approve, MT-3.6-04; null for note actions on a review that never had a submission, e.g. T9).
  @BuiltValueField(wireName: r'resolution_id')
  String? get resolutionId;

  /// approve | request_changes | reassign (Section 9.2's three).  * `approve` - approve * `request_changes` - request_changes * `reassign` - reassign
  @BuiltValueField(wireName: r'decision')
  DecisionEnum get decision;
  // enum decisionEnum {  approve,  request_changes,  reassign,  };

  /// The reviewer's note — mandatory for request_changes (T16 guard); it becomes the Task's latest_feedback (Section 11.5).
  @BuiltValueField(wireName: r'note')
  String get note;

  /// The acting principal: owner user id (web) or device id (mobile).
  @BuiltValueField(wireName: r'decided_by')
  String get decidedBy;

  /// web | mobile — Section 7.2's two review channels (13/14).  * `web` - web * `mobile` - mobile
  @BuiltValueField(wireName: r'decided_via')
  DecidedViaEnum get decidedVia;
  // enum decidedViaEnum {  web,  mobile,  };

  /// Server clock at insertion (P7).
  @BuiltValueField(wireName: r'decided_at')
  DateTime get decidedAt;

  ReviewDecisionRecord._();

  factory ReviewDecisionRecord([void updates(ReviewDecisionRecordBuilder b)]) =
      _$ReviewDecisionRecord;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ReviewDecisionRecordBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<ReviewDecisionRecord> get serializer =>
      _$ReviewDecisionRecordSerializer();
}

class _$ReviewDecisionRecordSerializer
    implements PrimitiveSerializer<ReviewDecisionRecord> {
  @override
  final Iterable<Type> types = const [
    ReviewDecisionRecord,
    _$ReviewDecisionRecord
  ];

  @override
  final String wireName = r'ReviewDecisionRecord';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ReviewDecisionRecord object, {
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
    yield r'resolution_id';
    yield object.resolutionId == null
        ? null
        : serializers.serialize(
            object.resolutionId,
            specifiedType: const FullType.nullable(String),
          );
    yield r'decision';
    yield serializers.serialize(
      object.decision,
      specifiedType: const FullType(DecisionEnum),
    );
    yield r'note';
    yield serializers.serialize(
      object.note,
      specifiedType: const FullType(String),
    );
    yield r'decided_by';
    yield serializers.serialize(
      object.decidedBy,
      specifiedType: const FullType(String),
    );
    yield r'decided_via';
    yield serializers.serialize(
      object.decidedVia,
      specifiedType: const FullType(DecidedViaEnum),
    );
    yield r'decided_at';
    yield serializers.serialize(
      object.decidedAt,
      specifiedType: const FullType(DateTime),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    ReviewDecisionRecord object, {
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
    required ReviewDecisionRecordBuilder result,
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
        case r'resolution_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.resolutionId = valueDes;
          break;
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
            specifiedType: const FullType(String),
          ) as String;
          result.note = valueDes;
          break;
        case r'decided_by':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.decidedBy = valueDes;
          break;
        case r'decided_via':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DecidedViaEnum),
          ) as DecidedViaEnum;
          result.decidedVia = valueDes;
          break;
        case r'decided_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.decidedAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ReviewDecisionRecord deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ReviewDecisionRecordBuilder();
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
