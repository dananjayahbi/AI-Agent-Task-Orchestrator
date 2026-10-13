//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'state_counts.g.dart';

/// The six canonical G-01/ADR-010 state counts, always all present.  Zero-filled by the service: a state with no tasks reads ``0``, never an absent key — the mobile card renders every column from these keys and never invents its own (G-01; MT-5.6-01).
///
/// Properties:
/// * [draft] - Tasks in draft (Section 8.2 T1).
/// * [pending] - Tasks visible to agents for claiming (Section 8.2).
/// * [inProgress] - Tasks under an active coder lease (Section 8.6).
/// * [toBeAudited] - Submissions awaiting an auditor claim (Section 8.2).
/// * [inHumanReview] - Tasks escalated to the Owner — the mobile 'needs review' banner derives from this count (Section 14.1; FR-MOB-04).
/// * [completed] - Completed tasks; immutable except archive (Section 7.4 rule 3).
@BuiltValue()
abstract class StateCounts implements Built<StateCounts, StateCountsBuilder> {
  /// Tasks in draft (Section 8.2 T1).
  @BuiltValueField(wireName: r'draft')
  int get draft;

  /// Tasks visible to agents for claiming (Section 8.2).
  @BuiltValueField(wireName: r'pending')
  int get pending;

  /// Tasks under an active coder lease (Section 8.6).
  @BuiltValueField(wireName: r'in_progress')
  int get inProgress;

  /// Submissions awaiting an auditor claim (Section 8.2).
  @BuiltValueField(wireName: r'to_be_audited')
  int get toBeAudited;

  /// Tasks escalated to the Owner — the mobile 'needs review' banner derives from this count (Section 14.1; FR-MOB-04).
  @BuiltValueField(wireName: r'in_human_review')
  int get inHumanReview;

  /// Completed tasks; immutable except archive (Section 7.4 rule 3).
  @BuiltValueField(wireName: r'completed')
  int get completed;

  StateCounts._();

  factory StateCounts([void updates(StateCountsBuilder b)]) = _$StateCounts;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(StateCountsBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<StateCounts> get serializer => _$StateCountsSerializer();
}

class _$StateCountsSerializer implements PrimitiveSerializer<StateCounts> {
  @override
  final Iterable<Type> types = const [StateCounts, _$StateCounts];

  @override
  final String wireName = r'StateCounts';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    StateCounts object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'draft';
    yield serializers.serialize(
      object.draft,
      specifiedType: const FullType(int),
    );
    yield r'pending';
    yield serializers.serialize(
      object.pending,
      specifiedType: const FullType(int),
    );
    yield r'in_progress';
    yield serializers.serialize(
      object.inProgress,
      specifiedType: const FullType(int),
    );
    yield r'to_be_audited';
    yield serializers.serialize(
      object.toBeAudited,
      specifiedType: const FullType(int),
    );
    yield r'in_human_review';
    yield serializers.serialize(
      object.inHumanReview,
      specifiedType: const FullType(int),
    );
    yield r'completed';
    yield serializers.serialize(
      object.completed,
      specifiedType: const FullType(int),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    StateCounts object, {
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
    required StateCountsBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'draft':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.draft = valueDes;
          break;
        case r'pending':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.pending = valueDes;
          break;
        case r'in_progress':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.inProgress = valueDes;
          break;
        case r'to_be_audited':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.toBeAudited = valueDes;
          break;
        case r'in_human_review':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.inHumanReview = valueDes;
          break;
        case r'completed':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.completed = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  StateCounts deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = StateCountsBuilder();
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
