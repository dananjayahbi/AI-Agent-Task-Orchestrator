//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'queue_task_state.g.dart';

/// The post-mutation task identity the start/result responses carry.
///
/// Properties:
/// * [id] - Section 7.3 task id.
/// * [state] - Canonical state after the mutation — in_human_review or to_be_audited on start; completed (T17) or in_human_review (T18) after a result.
/// * [version] - Optimistic-lock version after the row (7.2).
/// * [reviewReason] - Section 8.4 member — merge_conflict after T18, else unchanged.
/// * [mergeStatus] - none | pending | merging | merged | conflict | failed (7.2).
@BuiltValue()
abstract class QueueTaskState
    implements Built<QueueTaskState, QueueTaskStateBuilder> {
  /// Section 7.3 task id.
  @BuiltValueField(wireName: r'id')
  String get id;

  /// Canonical state after the mutation — in_human_review or to_be_audited on start; completed (T17) or in_human_review (T18) after a result.
  @BuiltValueField(wireName: r'state')
  String get state;

  /// Optimistic-lock version after the row (7.2).
  @BuiltValueField(wireName: r'version')
  int get version;

  /// Section 8.4 member — merge_conflict after T18, else unchanged.
  @BuiltValueField(wireName: r'review_reason')
  String? get reviewReason;

  /// none | pending | merging | merged | conflict | failed (7.2).
  @BuiltValueField(wireName: r'merge_status')
  String get mergeStatus;

  QueueTaskState._();

  factory QueueTaskState([void updates(QueueTaskStateBuilder b)]) =
      _$QueueTaskState;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(QueueTaskStateBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<QueueTaskState> get serializer =>
      _$QueueTaskStateSerializer();
}

class _$QueueTaskStateSerializer
    implements PrimitiveSerializer<QueueTaskState> {
  @override
  final Iterable<Type> types = const [QueueTaskState, _$QueueTaskState];

  @override
  final String wireName = r'QueueTaskState';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    QueueTaskState object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'state';
    yield serializers.serialize(
      object.state,
      specifiedType: const FullType(String),
    );
    yield r'version';
    yield serializers.serialize(
      object.version,
      specifiedType: const FullType(int),
    );
    yield r'review_reason';
    yield object.reviewReason == null
        ? null
        : serializers.serialize(
            object.reviewReason,
            specifiedType: const FullType.nullable(String),
          );
    yield r'merge_status';
    yield serializers.serialize(
      object.mergeStatus,
      specifiedType: const FullType(String),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    QueueTaskState object, {
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
    required QueueTaskStateBuilder result,
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
        case r'state':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.state = valueDes;
          break;
        case r'version':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.version = valueDes;
          break;
        case r'review_reason':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.reviewReason = valueDes;
          break;
        case r'merge_status':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.mergeStatus = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  QueueTaskState deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = QueueTaskStateBuilder();
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
