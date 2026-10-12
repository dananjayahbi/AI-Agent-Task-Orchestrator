//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/active_status_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'patched_project_update.g.dart';

/// PATCH /projects/{pid} body — every FR-PRJ-02 mutable field, optional.
///
/// Properties:
/// * [name]
/// * [repoPath]
/// * [defaultBranch]
/// * [systemPromptRules]
/// * [activeStatus] - Transitions among active | paused | archived (FR-PRJ-04).  * `active` - active * `paused` - paused * `archived` - archived
@BuiltValue()
abstract class PatchedProjectUpdate
    implements Built<PatchedProjectUpdate, PatchedProjectUpdateBuilder> {
  @BuiltValueField(wireName: r'name')
  String? get name;

  @BuiltValueField(wireName: r'repo_path')
  String? get repoPath;

  @BuiltValueField(wireName: r'default_branch')
  String? get defaultBranch;

  @BuiltValueField(wireName: r'system_prompt_rules')
  String? get systemPromptRules;

  /// Transitions among active | paused | archived (FR-PRJ-04).  * `active` - active * `paused` - paused * `archived` - archived
  @BuiltValueField(wireName: r'active_status')
  ActiveStatusEnum? get activeStatus;
  // enum activeStatusEnum {  active,  paused,  archived,  };

  PatchedProjectUpdate._();

  factory PatchedProjectUpdate([void updates(PatchedProjectUpdateBuilder b)]) =
      _$PatchedProjectUpdate;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(PatchedProjectUpdateBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<PatchedProjectUpdate> get serializer =>
      _$PatchedProjectUpdateSerializer();
}

class _$PatchedProjectUpdateSerializer
    implements PrimitiveSerializer<PatchedProjectUpdate> {
  @override
  final Iterable<Type> types = const [
    PatchedProjectUpdate,
    _$PatchedProjectUpdate
  ];

  @override
  final String wireName = r'PatchedProjectUpdate';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    PatchedProjectUpdate object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    if (object.name != null) {
      yield r'name';
      yield serializers.serialize(
        object.name,
        specifiedType: const FullType(String),
      );
    }
    if (object.repoPath != null) {
      yield r'repo_path';
      yield serializers.serialize(
        object.repoPath,
        specifiedType: const FullType(String),
      );
    }
    if (object.defaultBranch != null) {
      yield r'default_branch';
      yield serializers.serialize(
        object.defaultBranch,
        specifiedType: const FullType(String),
      );
    }
    if (object.systemPromptRules != null) {
      yield r'system_prompt_rules';
      yield serializers.serialize(
        object.systemPromptRules,
        specifiedType: const FullType(String),
      );
    }
    if (object.activeStatus != null) {
      yield r'active_status';
      yield serializers.serialize(
        object.activeStatus,
        specifiedType: const FullType(ActiveStatusEnum),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    PatchedProjectUpdate object, {
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
    required PatchedProjectUpdateBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'name':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.name = valueDes;
          break;
        case r'repo_path':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.repoPath = valueDes;
          break;
        case r'default_branch':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.defaultBranch = valueDes;
          break;
        case r'system_prompt_rules':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.systemPromptRules = valueDes;
          break;
        case r'active_status':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(ActiveStatusEnum),
          ) as ActiveStatusEnum?;
          if (valueDes == null) continue;
          result.activeStatus = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  PatchedProjectUpdate deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = PatchedProjectUpdateBuilder();
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
