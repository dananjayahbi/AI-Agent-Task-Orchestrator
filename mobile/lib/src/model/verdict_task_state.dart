//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'verdict_task_state.g.dart';

/// The post-transition task identity the verdict response carries.
///
/// Properties:
/// * [id]
/// * [state] - Canonical state after the dispatch — in_human_review (T14, the fail-closed escalate) or to_be_audited with merge_status pending (T13, engine-approved; Section 8.2).
/// * [version] - Optimistic-lock version after the row (7.2).
/// * [reviewReason] - Section 8.4 member T14 set; null on the T13 approve branch.
/// * [mergeStatus] - none | pending | merging | merged | conflict | failed (7.2) — pending marks T13's merge-pending sub-status.
@BuiltValue()
abstract class VerdictTaskState
    implements Built<VerdictTaskState, VerdictTaskStateBuilder> {
  @BuiltValueField(wireName: r'id')
  String get id;

  /// Canonical state after the dispatch — in_human_review (T14, the fail-closed escalate) or to_be_audited with merge_status pending (T13, engine-approved; Section 8.2).
  @BuiltValueField(wireName: r'state')
  String get state;

  /// Optimistic-lock version after the row (7.2).
  @BuiltValueField(wireName: r'version')
  int get version;

  /// Section 8.4 member T14 set; null on the T13 approve branch.
  @BuiltValueField(wireName: r'review_reason')
  String? get reviewReason;

  /// none | pending | merging | merged | conflict | failed (7.2) — pending marks T13's merge-pending sub-status.
  @BuiltValueField(wireName: r'merge_status')
  String get mergeStatus;

  VerdictTaskState._();

  factory VerdictTaskState([void updates(VerdictTaskStateBuilder b)]) =
      _$VerdictTaskState;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(VerdictTaskStateBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<VerdictTaskState> get serializer =>
      _$VerdictTaskStateSerializer();
}

class _$VerdictTaskStateSerializer
    implements PrimitiveSerializer<VerdictTaskState> {
  @override
  final Iterable<Type> types = const [VerdictTaskState, _$VerdictTaskState];

  @override
  final String wireName = r'VerdictTaskState';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    VerdictTaskState object, {
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
    VerdictTaskState object, {
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
    required VerdictTaskStateBuilder result,
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
  VerdictTaskState deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = VerdictTaskStateBuilder();
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
