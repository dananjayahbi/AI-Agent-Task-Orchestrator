//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/resolution_task_state.dart';
import 'package:orchestrator_mobile/src/model/resolution.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'resolution_write_response.g.dart';

/// The frozen submission response — Section 10.5 outcome reporting.
///
/// Properties:
/// * [resolution] - The stored Section 7.2 row.
/// * [task] - Post-transition task identity — the outcome the agent is told.
/// * [trigger] - Which Section 8.2 row fired: submit (T7), submit_flagged (T8), submit_unreviewed / submit_policy_approved (T10's two branches).
/// * [scopeViolations] - Changed files outside target_scope (Section 12.3; empty when clean) — the offending paths captured for review_reason scope_violation.
@BuiltValue()
abstract class ResolutionWriteResponse
    implements Built<ResolutionWriteResponse, ResolutionWriteResponseBuilder> {
  /// The stored Section 7.2 row.
  @BuiltValueField(wireName: r'resolution')
  Resolution get resolution;

  /// Post-transition task identity — the outcome the agent is told.
  @BuiltValueField(wireName: r'task')
  ResolutionTaskState get task;

  /// Which Section 8.2 row fired: submit (T7), submit_flagged (T8), submit_unreviewed / submit_policy_approved (T10's two branches).
  @BuiltValueField(wireName: r'trigger')
  String get trigger;

  /// Changed files outside target_scope (Section 12.3; empty when clean) — the offending paths captured for review_reason scope_violation.
  @BuiltValueField(wireName: r'scope_violations')
  BuiltList<String> get scopeViolations;

  ResolutionWriteResponse._();

  factory ResolutionWriteResponse(
          [void updates(ResolutionWriteResponseBuilder b)]) =
      _$ResolutionWriteResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ResolutionWriteResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<ResolutionWriteResponse> get serializer =>
      _$ResolutionWriteResponseSerializer();
}

class _$ResolutionWriteResponseSerializer
    implements PrimitiveSerializer<ResolutionWriteResponse> {
  @override
  final Iterable<Type> types = const [
    ResolutionWriteResponse,
    _$ResolutionWriteResponse
  ];

  @override
  final String wireName = r'ResolutionWriteResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ResolutionWriteResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'resolution';
    yield serializers.serialize(
      object.resolution,
      specifiedType: const FullType(Resolution),
    );
    yield r'task';
    yield serializers.serialize(
      object.task,
      specifiedType: const FullType(ResolutionTaskState),
    );
    yield r'trigger';
    yield serializers.serialize(
      object.trigger,
      specifiedType: const FullType(String),
    );
    yield r'scope_violations';
    yield serializers.serialize(
      object.scopeViolations,
      specifiedType: const FullType(BuiltList, [FullType(String)]),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    ResolutionWriteResponse object, {
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
    required ResolutionWriteResponseBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'resolution':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(Resolution),
          ) as Resolution;
          result.resolution.replace(valueDes);
          break;
        case r'task':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(ResolutionTaskState),
          ) as ResolutionTaskState;
          result.task.replace(valueDes);
          break;
        case r'trigger':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.trigger = valueDes;
          break;
        case r'scope_violations':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(BuiltList, [FullType(String)]),
          ) as BuiltList<String>;
          result.scopeViolations.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ResolutionWriteResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ResolutionWriteResponseBuilder();
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
