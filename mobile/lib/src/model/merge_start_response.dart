//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/queue_task_state.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'merge_start_response.g.dart';

/// Start's response — the post-claim identity the executor chains on.
///
/// Properties:
/// * [task] - merge_status is now 'merging' and version incremented (7.2).
@BuiltValue()
abstract class MergeStartResponse
    implements Built<MergeStartResponse, MergeStartResponseBuilder> {
  /// merge_status is now 'merging' and version incremented (7.2).
  @BuiltValueField(wireName: r'task')
  QueueTaskState get task;

  MergeStartResponse._();

  factory MergeStartResponse([void updates(MergeStartResponseBuilder b)]) =
      _$MergeStartResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(MergeStartResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<MergeStartResponse> get serializer =>
      _$MergeStartResponseSerializer();
}

class _$MergeStartResponseSerializer
    implements PrimitiveSerializer<MergeStartResponse> {
  @override
  final Iterable<Type> types = const [MergeStartResponse, _$MergeStartResponse];

  @override
  final String wireName = r'MergeStartResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    MergeStartResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'task';
    yield serializers.serialize(
      object.task,
      specifiedType: const FullType(QueueTaskState),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    MergeStartResponse object, {
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
    required MergeStartResponseBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'task':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(QueueTaskState),
          ) as QueueTaskState;
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
  MergeStartResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = MergeStartResponseBuilder();
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
