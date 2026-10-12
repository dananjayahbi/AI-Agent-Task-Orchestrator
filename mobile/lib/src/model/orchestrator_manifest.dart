//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/agent_hints.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'orchestrator_manifest.g.dart';

/// OrchestratorManifest
///
/// Properties:
/// * [dollarSchema] - Location of the manifest schema (Section 10.3).
/// * [schemaVersion] - Manifest generation — always 1 (Section 10.3).
/// * [projectId] - Canonical PID + five digits (Section 7.3).
/// * [projectName]
/// * [orchestratorApi] - API base URL from ORCHESTRATOR_API_BASE_URL (Section 9.10 / NFR-06 — configuration, never code).
/// * [defaultBranch]
/// * [autoBranchPrefix] - Policy branch_prefix with {PID} resolved (G-09).
/// * [auditRequiredDefault] - Policy default for new tasks (Section 7.2).
/// * [agentHints] - All hint keys optional (Section 10.3).
@BuiltValue()
abstract class OrchestratorManifest
    implements Built<OrchestratorManifest, OrchestratorManifestBuilder> {
  /// Location of the manifest schema (Section 10.3).
  @BuiltValueField(wireName: r'$schema')
  String get dollarSchema;

  /// Manifest generation — always 1 (Section 10.3).
  @BuiltValueField(wireName: r'schema_version')
  int get schemaVersion;

  /// Canonical PID + five digits (Section 7.3).
  @BuiltValueField(wireName: r'project_id')
  String get projectId;

  @BuiltValueField(wireName: r'project_name')
  String get projectName;

  /// API base URL from ORCHESTRATOR_API_BASE_URL (Section 9.10 / NFR-06 — configuration, never code).
  @BuiltValueField(wireName: r'orchestrator_api')
  String get orchestratorApi;

  @BuiltValueField(wireName: r'default_branch')
  String get defaultBranch;

  /// Policy branch_prefix with {PID} resolved (G-09).
  @BuiltValueField(wireName: r'auto_branch_prefix')
  String get autoBranchPrefix;

  /// Policy default for new tasks (Section 7.2).
  @BuiltValueField(wireName: r'audit_required_default')
  bool get auditRequiredDefault;

  /// All hint keys optional (Section 10.3).
  @BuiltValueField(wireName: r'agent_hints')
  AgentHints? get agentHints;

  OrchestratorManifest._();

  factory OrchestratorManifest([void updates(OrchestratorManifestBuilder b)]) =
      _$OrchestratorManifest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(OrchestratorManifestBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<OrchestratorManifest> get serializer =>
      _$OrchestratorManifestSerializer();
}

class _$OrchestratorManifestSerializer
    implements PrimitiveSerializer<OrchestratorManifest> {
  @override
  final Iterable<Type> types = const [
    OrchestratorManifest,
    _$OrchestratorManifest
  ];

  @override
  final String wireName = r'OrchestratorManifest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    OrchestratorManifest object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'$schema';
    yield serializers.serialize(
      object.dollarSchema,
      specifiedType: const FullType(String),
    );
    yield r'schema_version';
    yield serializers.serialize(
      object.schemaVersion,
      specifiedType: const FullType(int),
    );
    yield r'project_id';
    yield serializers.serialize(
      object.projectId,
      specifiedType: const FullType(String),
    );
    yield r'project_name';
    yield serializers.serialize(
      object.projectName,
      specifiedType: const FullType(String),
    );
    yield r'orchestrator_api';
    yield serializers.serialize(
      object.orchestratorApi,
      specifiedType: const FullType(String),
    );
    yield r'default_branch';
    yield serializers.serialize(
      object.defaultBranch,
      specifiedType: const FullType(String),
    );
    yield r'auto_branch_prefix';
    yield serializers.serialize(
      object.autoBranchPrefix,
      specifiedType: const FullType(String),
    );
    yield r'audit_required_default';
    yield serializers.serialize(
      object.auditRequiredDefault,
      specifiedType: const FullType(bool),
    );
    if (object.agentHints != null) {
      yield r'agent_hints';
      yield serializers.serialize(
        object.agentHints,
        specifiedType: const FullType(AgentHints),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    OrchestratorManifest object, {
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
    required OrchestratorManifestBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'$schema':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.dollarSchema = valueDes;
          break;
        case r'schema_version':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.schemaVersion = valueDes;
          break;
        case r'project_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.projectId = valueDes;
          break;
        case r'project_name':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.projectName = valueDes;
          break;
        case r'orchestrator_api':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.orchestratorApi = valueDes;
          break;
        case r'default_branch':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.defaultBranch = valueDes;
          break;
        case r'auto_branch_prefix':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.autoBranchPrefix = valueDes;
          break;
        case r'audit_required_default':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.auditRequiredDefault = valueDes;
          break;
        case r'agent_hints':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(AgentHints),
          ) as AgentHints?;
          if (valueDes == null) continue;
          result.agentHints.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  OrchestratorManifest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = OrchestratorManifestBuilder();
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
