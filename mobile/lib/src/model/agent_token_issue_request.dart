//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'agent_token_issue_request.g.dart';

/// POST /tokens/agent body: which project, which roles.
///
/// Properties:
/// * [projectId] - Target project id (PID + five digits, Section 7.3).
/// * [scopes] - Agent roles this token may act as (Section 12.2 matrix roles). Allowed: coder, auditor, decomposer, merge_executor.
@BuiltValue()
abstract class AgentTokenIssueRequest
    implements Built<AgentTokenIssueRequest, AgentTokenIssueRequestBuilder> {
  /// Target project id (PID + five digits, Section 7.3).
  @BuiltValueField(wireName: r'project_id')
  String get projectId;

  /// Agent roles this token may act as (Section 12.2 matrix roles). Allowed: coder, auditor, decomposer, merge_executor.
  @BuiltValueField(wireName: r'scopes')
  BuiltList<String>? get scopes;

  AgentTokenIssueRequest._();

  factory AgentTokenIssueRequest(
          [void updates(AgentTokenIssueRequestBuilder b)]) =
      _$AgentTokenIssueRequest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AgentTokenIssueRequestBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AgentTokenIssueRequest> get serializer =>
      _$AgentTokenIssueRequestSerializer();
}

class _$AgentTokenIssueRequestSerializer
    implements PrimitiveSerializer<AgentTokenIssueRequest> {
  @override
  final Iterable<Type> types = const [
    AgentTokenIssueRequest,
    _$AgentTokenIssueRequest
  ];

  @override
  final String wireName = r'AgentTokenIssueRequest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AgentTokenIssueRequest object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'project_id';
    yield serializers.serialize(
      object.projectId,
      specifiedType: const FullType(String),
    );
    if (object.scopes != null) {
      yield r'scopes';
      yield serializers.serialize(
        object.scopes,
        specifiedType: const FullType(BuiltList, [FullType(String)]),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    AgentTokenIssueRequest object, {
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
    required AgentTokenIssueRequestBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'project_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.projectId = valueDes;
          break;
        case r'scopes':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.scopes.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AgentTokenIssueRequest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AgentTokenIssueRequestBuilder();
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
