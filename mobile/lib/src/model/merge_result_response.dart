//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/queue_task_state.dart';
import 'package:orchestrator_mobile/src/model/result_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'merge_result_response.g.dart';

/// Result's response — the post-transition identity plus the echo.
///
/// Properties:
/// * [task] - completed + merged (T17) or in_human_review + conflict/failed with review_reason merge_conflict (T18).
/// * [result] - The reported outcome, echoed.  * `succeeded` - succeeded * `conflict` - conflict * `failed` - failed
/// * [sha] - The resulting sha on success; null on the T18 failure branches.
@BuiltValue()
abstract class MergeResultResponse
    implements Built<MergeResultResponse, MergeResultResponseBuilder> {
  /// completed + merged (T17) or in_human_review + conflict/failed with review_reason merge_conflict (T18).
  @BuiltValueField(wireName: r'task')
  QueueTaskState get task;

  /// The reported outcome, echoed.  * `succeeded` - succeeded * `conflict` - conflict * `failed` - failed
  @BuiltValueField(wireName: r'result')
  ResultEnum get result;
  // enum resultEnum {  succeeded,  conflict,  failed,  };

  /// The resulting sha on success; null on the T18 failure branches.
  @BuiltValueField(wireName: r'sha')
  String? get sha;

  MergeResultResponse._();

  factory MergeResultResponse([void updates(MergeResultResponseBuilder b)]) =
      _$MergeResultResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(MergeResultResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<MergeResultResponse> get serializer =>
      _$MergeResultResponseSerializer();
}

class _$MergeResultResponseSerializer
    implements PrimitiveSerializer<MergeResultResponse> {
  @override
  final Iterable<Type> types = const [
    MergeResultResponse,
    _$MergeResultResponse
  ];

  @override
  final String wireName = r'MergeResultResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    MergeResultResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'task';
    yield serializers.serialize(
      object.task,
      specifiedType: const FullType(QueueTaskState),
    );
    yield r'result';
    yield serializers.serialize(
      object.result,
      specifiedType: const FullType(ResultEnum),
    );
    yield r'sha';
    yield object.sha == null
        ? null
        : serializers.serialize(
            object.sha,
            specifiedType: const FullType.nullable(String),
          );
  }

  @override
  Object serialize(
    Serializers serializers,
    MergeResultResponse object, {
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
    required MergeResultResponseBuilder result,
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
        case r'result':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(ResultEnum),
          ) as ResultEnum;
          result.result = valueDes;
          break;
        case r'sha':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.sha = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  MergeResultResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = MergeResultResponseBuilder();
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
