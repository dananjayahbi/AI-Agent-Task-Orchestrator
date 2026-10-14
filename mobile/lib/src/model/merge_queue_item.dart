//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'merge_queue_item.g.dart';

/// One pending task in the queue (Section 9.2 GET /merge/pending).
///
/// Properties:
/// * [id] - Section 7.3 task id — the `{task}` path segment.
/// * [projectId] - Project the entry belongs to (ADR-004 scope).
/// * [title] - Section 7.2 title — the queue's human label.
/// * [state] - Carrier state: in_human_review (T15 approve) or to_be_audited (T10/T13 engine-approved) — Section 8.1's sub-status rides these two.
/// * [version] - Optimistic-lock version (7.2) — chain it onto start/result.
/// * [mergeStatus] - Always 'pending' in this listing (the Section 8.1 sub-status).
/// * [branchName] - Current attempt's branch (Section 7.2) the executor merges into the default branch; null only if the carrier somehow lost its resolution.
/// * [mergeStrategy] - The project policy's Section 7.2 strategy riding the row (squash | merge_commit | fast_forward_only; default squash) — the executor never configures strategy itself; manual entries are resolved by the queue-side guard and never appear here (OQ-06).
@BuiltValue()
abstract class MergeQueueItem
    implements Built<MergeQueueItem, MergeQueueItemBuilder> {
  /// Section 7.3 task id — the `{task}` path segment.
  @BuiltValueField(wireName: r'id')
  String get id;

  /// Project the entry belongs to (ADR-004 scope).
  @BuiltValueField(wireName: r'project_id')
  String get projectId;

  /// Section 7.2 title — the queue's human label.
  @BuiltValueField(wireName: r'title')
  String get title;

  /// Carrier state: in_human_review (T15 approve) or to_be_audited (T10/T13 engine-approved) — Section 8.1's sub-status rides these two.
  @BuiltValueField(wireName: r'state')
  String get state;

  /// Optimistic-lock version (7.2) — chain it onto start/result.
  @BuiltValueField(wireName: r'version')
  int get version;

  /// Always 'pending' in this listing (the Section 8.1 sub-status).
  @BuiltValueField(wireName: r'merge_status')
  String get mergeStatus;

  /// Current attempt's branch (Section 7.2) the executor merges into the default branch; null only if the carrier somehow lost its resolution.
  @BuiltValueField(wireName: r'branch_name')
  String? get branchName;

  /// The project policy's Section 7.2 strategy riding the row (squash | merge_commit | fast_forward_only; default squash) — the executor never configures strategy itself; manual entries are resolved by the queue-side guard and never appear here (OQ-06).
  @BuiltValueField(wireName: r'merge_strategy')
  String get mergeStrategy;

  MergeQueueItem._();

  factory MergeQueueItem([void updates(MergeQueueItemBuilder b)]) =
      _$MergeQueueItem;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(MergeQueueItemBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<MergeQueueItem> get serializer =>
      _$MergeQueueItemSerializer();
}

class _$MergeQueueItemSerializer
    implements PrimitiveSerializer<MergeQueueItem> {
  @override
  final Iterable<Type> types = const [MergeQueueItem, _$MergeQueueItem];

  @override
  final String wireName = r'MergeQueueItem';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    MergeQueueItem object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'project_id';
    yield serializers.serialize(
      object.projectId,
      specifiedType: const FullType(String),
    );
    yield r'title';
    yield serializers.serialize(
      object.title,
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
    yield r'merge_status';
    yield serializers.serialize(
      object.mergeStatus,
      specifiedType: const FullType(String),
    );
    yield r'branch_name';
    yield object.branchName == null
        ? null
        : serializers.serialize(
            object.branchName,
            specifiedType: const FullType.nullable(String),
          );
    yield r'merge_strategy';
    yield serializers.serialize(
      object.mergeStrategy,
      specifiedType: const FullType(String),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    MergeQueueItem object, {
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
    required MergeQueueItemBuilder result,
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
        case r'project_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.projectId = valueDes;
          break;
        case r'title':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.title = valueDes;
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
        case r'merge_status':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.mergeStatus = valueDes;
          break;
        case r'branch_name':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.branchName = valueDes;
          break;
        case r'merge_strategy':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.mergeStrategy = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  MergeQueueItem deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = MergeQueueItemBuilder();
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
