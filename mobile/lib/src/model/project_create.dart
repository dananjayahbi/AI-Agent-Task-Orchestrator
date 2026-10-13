//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/policy_preset_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'project_create.g.dart';

/// POST /projects body — Section 9.2 create inputs + WP-3.1 preset.
///
/// Properties:
/// * [name]
/// * [repoPath]
/// * [defaultBranch]
/// * [systemPromptRules] - Optional at creation; editable afterwards via PATCH.
/// * [policyPreset] - Optional framework preset (WP-3.1, MT-3.1-02): seeds the new project's policy with the preset's critical/migration/sensitive globs. Omitted = the Section 7.2 stock defaults. Unknown ids are VALIDATION_ERROR.  * `django` - django * `nextjs` - nextjs * `flutter` - flutter
@BuiltValue()
abstract class ProjectCreate
    implements Built<ProjectCreate, ProjectCreateBuilder> {
  @BuiltValueField(wireName: r'name')
  String get name;

  @BuiltValueField(wireName: r'repo_path')
  String get repoPath;

  @BuiltValueField(wireName: r'default_branch')
  String get defaultBranch;

  /// Optional at creation; editable afterwards via PATCH.
  @BuiltValueField(wireName: r'system_prompt_rules')
  String? get systemPromptRules;

  /// Optional framework preset (WP-3.1, MT-3.1-02): seeds the new project's policy with the preset's critical/migration/sensitive globs. Omitted = the Section 7.2 stock defaults. Unknown ids are VALIDATION_ERROR.  * `django` - django * `nextjs` - nextjs * `flutter` - flutter
  @BuiltValueField(wireName: r'policy_preset')
  PolicyPresetEnum? get policyPreset;
  // enum policyPresetEnum {  django,  nextjs,  flutter,  };

  ProjectCreate._();

  factory ProjectCreate([void updates(ProjectCreateBuilder b)]) =
      _$ProjectCreate;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ProjectCreateBuilder b) => b..systemPromptRules = '';

  @BuiltValueSerializer(custom: true)
  static Serializer<ProjectCreate> get serializer =>
      _$ProjectCreateSerializer();
}

class _$ProjectCreateSerializer implements PrimitiveSerializer<ProjectCreate> {
  @override
  final Iterable<Type> types = const [ProjectCreate, _$ProjectCreate];

  @override
  final String wireName = r'ProjectCreate';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ProjectCreate object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
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
    yield r'default_branch';
    yield serializers.serialize(
      object.defaultBranch,
      specifiedType: const FullType(String),
    );
    if (object.systemPromptRules != null) {
      yield r'system_prompt_rules';
      yield serializers.serialize(
        object.systemPromptRules,
        specifiedType: const FullType(String),
      );
    }
    if (object.policyPreset != null) {
      yield r'policy_preset';
      yield serializers.serialize(
        object.policyPreset,
        specifiedType: const FullType(PolicyPresetEnum),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    ProjectCreate object, {
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
    required ProjectCreateBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
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
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.systemPromptRules = valueDes;
          break;
        case r'policy_preset':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(PolicyPresetEnum),
          ) as PolicyPresetEnum?;
          if (valueDes == null) continue;
          result.policyPreset = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ProjectCreate deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ProjectCreateBuilder();
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
