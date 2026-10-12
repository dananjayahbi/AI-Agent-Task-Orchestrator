//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/active_status_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'project.g.dart';

/// GET representations of a project — Section 7.2 fields, in plan order.
///
/// Properties:
/// * [id] - Server-assigned PID + five digits (Section 7.3); immutable.
/// * [name]
/// * [repoPath] - Path as seen by the bridge host (informational for the backend).
/// * [activeStatus] - active | paused | archived (FR-PRJ-04).  * `active` - active * `paused` - paused * `archived` - archived
/// * [defaultBranch]
/// * [systemPromptRules] - Markdown text fed into the rules block (Section 10.6).
/// * [agentPolicy] - The project's one-to-one Project Policy row (Section 7.1).
/// * [taskCounter] - Atomic task index source for MT-1.4-02 (starts at 0).
/// * [createdAt]
/// * [updatedAt]
@BuiltValue()
abstract class Project implements Built<Project, ProjectBuilder> {
  /// Server-assigned PID + five digits (Section 7.3); immutable.
  @BuiltValueField(wireName: r'id')
  String get id;

  @BuiltValueField(wireName: r'name')
  String get name;

  /// Path as seen by the bridge host (informational for the backend).
  @BuiltValueField(wireName: r'repo_path')
  String get repoPath;

  /// active | paused | archived (FR-PRJ-04).  * `active` - active * `paused` - paused * `archived` - archived
  @BuiltValueField(wireName: r'active_status')
  ActiveStatusEnum get activeStatus;
  // enum activeStatusEnum {  active,  paused,  archived,  };

  @BuiltValueField(wireName: r'default_branch')
  String get defaultBranch;

  /// Markdown text fed into the rules block (Section 10.6).
  @BuiltValueField(wireName: r'system_prompt_rules')
  String get systemPromptRules;

  /// The project's one-to-one Project Policy row (Section 7.1).
  @BuiltValueField(wireName: r'agent_policy')
  int get agentPolicy;

  /// Atomic task index source for MT-1.4-02 (starts at 0).
  @BuiltValueField(wireName: r'task_counter')
  int get taskCounter;

  @BuiltValueField(wireName: r'created_at')
  DateTime get createdAt;

  @BuiltValueField(wireName: r'updated_at')
  DateTime get updatedAt;

  Project._();

  factory Project([void updates(ProjectBuilder b)]) = _$Project;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ProjectBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<Project> get serializer => _$ProjectSerializer();
}

class _$ProjectSerializer implements PrimitiveSerializer<Project> {
  @override
  final Iterable<Type> types = const [Project, _$Project];

  @override
  final String wireName = r'Project';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    Project object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'name';
    yield serializers.serialize(
      object.name,
      specifiedType: const FullType(String),
    );
    yield r'repo_path';
    yield serializers.serialize(
      object.repoPath,
      specifiedType: const FullType(String),
    );
    yield r'active_status';
    yield serializers.serialize(
      object.activeStatus,
      specifiedType: const FullType(ActiveStatusEnum),
    );
    yield r'default_branch';
    yield serializers.serialize(
      object.defaultBranch,
      specifiedType: const FullType(String),
    );
    yield r'system_prompt_rules';
    yield serializers.serialize(
      object.systemPromptRules,
      specifiedType: const FullType(String),
    );
    yield r'agent_policy';
    yield serializers.serialize(
      object.agentPolicy,
      specifiedType: const FullType(int),
    );
    yield r'task_counter';
    yield serializers.serialize(
      object.taskCounter,
      specifiedType: const FullType(int),
    );
    yield r'created_at';
    yield serializers.serialize(
      object.createdAt,
      specifiedType: const FullType(DateTime),
    );
    yield r'updated_at';
    yield serializers.serialize(
      object.updatedAt,
      specifiedType: const FullType(DateTime),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    Project object, {
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
    required ProjectBuilder result,
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
        case r'name':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.name = valueDes;
          break;
        case r'repo_path':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.repoPath = valueDes;
          break;
        case r'active_status':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(ActiveStatusEnum),
          ) as ActiveStatusEnum;
          result.activeStatus = valueDes;
          break;
        case r'default_branch':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.defaultBranch = valueDes;
          break;
        case r'system_prompt_rules':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.systemPromptRules = valueDes;
          break;
        case r'agent_policy':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.agentPolicy = valueDes;
          break;
        case r'task_counter':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.taskCounter = valueDes;
          break;
        case r'created_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.createdAt = valueDes;
          break;
        case r'updated_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.updatedAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  Project deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ProjectBuilder();
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
