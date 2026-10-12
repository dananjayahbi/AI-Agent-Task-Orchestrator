//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/priority_enum.dart';
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'task_create.g.dart';

/// POST /projects/{pid}/tasks body — the FR-TSK-02 create inputs only.
///
/// Properties:
/// * [title]
/// * [description] - Markdown (FR-TSK-02); editable afterwards via PATCH.
/// * [acceptanceCriteria] - Acceptance-criteria strings (Section 7.2).
/// * [targetScope] - Repo-relative globs, validated on creation (Section 12.3).
/// * [testCommand]
/// * [priority] - FR-TSK-05; default medium (documented default — not a plan fact).  * `urgent` - urgent * `high` - high * `medium` - medium * `low` - low
@BuiltValue()
abstract class TaskCreate implements Built<TaskCreate, TaskCreateBuilder> {
  @BuiltValueField(wireName: r'title')
  String get title;

  /// Markdown (FR-TSK-02); editable afterwards via PATCH.
  @BuiltValueField(wireName: r'description')
  String? get description;

  /// Acceptance-criteria strings (Section 7.2).
  @BuiltValueField(wireName: r'acceptance_criteria')
  BuiltList<String>? get acceptanceCriteria;

  /// Repo-relative globs, validated on creation (Section 12.3).
  @BuiltValueField(wireName: r'target_scope')
  BuiltList<String>? get targetScope;

  @BuiltValueField(wireName: r'test_command')
  String? get testCommand;

  /// FR-TSK-05; default medium (documented default — not a plan fact).  * `urgent` - urgent * `high` - high * `medium` - medium * `low` - low
  @BuiltValueField(wireName: r'priority')
  PriorityEnum? get priority;
  // enum priorityEnum {  urgent,  high,  medium,  low,  };

  TaskCreate._();

  factory TaskCreate([void updates(TaskCreateBuilder b)]) = _$TaskCreate;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(TaskCreateBuilder b) => b
    ..description = ''
    ..testCommand = ''
    ..priority = PriorityEnum.medium;

  @BuiltValueSerializer(custom: true)
  static Serializer<TaskCreate> get serializer => _$TaskCreateSerializer();
}

class _$TaskCreateSerializer implements PrimitiveSerializer<TaskCreate> {
  @override
  final Iterable<Type> types = const [TaskCreate, _$TaskCreate];

  @override
  final String wireName = r'TaskCreate';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    TaskCreate object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'title';
    yield serializers.serialize(
      object.title,
      specifiedType: const FullType(String),
    );
    if (object.description != null) {
      yield r'description';
      yield serializers.serialize(
        object.description,
        specifiedType: const FullType(String),
      );
    }
    if (object.acceptanceCriteria != null) {
      yield r'acceptance_criteria';
      yield serializers.serialize(
        object.acceptanceCriteria,
        specifiedType: const FullType(BuiltList, [FullType(String)]),
      );
    }
    if (object.targetScope != null) {
      yield r'target_scope';
      yield serializers.serialize(
        object.targetScope,
        specifiedType: const FullType(BuiltList, [FullType(String)]),
      );
    }
    if (object.testCommand != null) {
      yield r'test_command';
      yield serializers.serialize(
        object.testCommand,
        specifiedType: const FullType(String),
      );
    }
    if (object.priority != null) {
      yield r'priority';
      yield serializers.serialize(
        object.priority,
        specifiedType: const FullType(PriorityEnum),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    TaskCreate object, {
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
    required TaskCreateBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'title':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.title = valueDes;
          break;
        case r'description':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.description = valueDes;
          break;
        case r'acceptance_criteria':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.acceptanceCriteria.replace(valueDes);
          break;
        case r'target_scope':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.targetScope.replace(valueDes);
          break;
        case r'test_command':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.testCommand = valueDes;
          break;
        case r'priority':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(PriorityEnum),
          ) as PriorityEnum?;
          if (valueDes == null) continue;
          result.priority = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  TaskCreate deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = TaskCreateBuilder();
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
