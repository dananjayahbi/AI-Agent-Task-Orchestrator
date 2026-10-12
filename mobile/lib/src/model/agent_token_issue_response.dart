//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/kind_e0d_enum.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'agent_token_issue_response.g.dart';

/// POST /tokens/agent 201 body: plaintext exactly once + row metadata.
///
/// Properties:
/// * [id]
/// * [kind]
/// * [projectId]
/// * [scopes]
/// * [expiresAt]
/// * [token] - The plaintext bearer token — returned exactly once, now. The server stores only its SHA-256 hash and cannot show it again (Section 7.2); lost tokens must be revoked and reissued.
@BuiltValue()
abstract class AgentTokenIssueResponse
    implements Built<AgentTokenIssueResponse, AgentTokenIssueResponseBuilder> {
  @BuiltValueField(wireName: r'id')
  int get id;

  @BuiltValueField(wireName: r'kind')
  KindE0dEnum get kind;
  // enum kindEnum {  owner_session,  agent,  device,  };

  @BuiltValueField(wireName: r'project_id')
  String? get projectId;

  @BuiltValueField(wireName: r'scopes')
  JsonObject? get scopes;

  @BuiltValueField(wireName: r'expires_at')
  DateTime? get expiresAt;

  /// The plaintext bearer token — returned exactly once, now. The server stores only its SHA-256 hash and cannot show it again (Section 7.2); lost tokens must be revoked and reissued.
  @BuiltValueField(wireName: r'token')
  String get token;

  AgentTokenIssueResponse._();

  factory AgentTokenIssueResponse(
          [void updates(AgentTokenIssueResponseBuilder b)]) =
      _$AgentTokenIssueResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AgentTokenIssueResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AgentTokenIssueResponse> get serializer =>
      _$AgentTokenIssueResponseSerializer();
}

class _$AgentTokenIssueResponseSerializer
    implements PrimitiveSerializer<AgentTokenIssueResponse> {
  @override
  final Iterable<Type> types = const [
    AgentTokenIssueResponse,
    _$AgentTokenIssueResponse
  ];

  @override
  final String wireName = r'AgentTokenIssueResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AgentTokenIssueResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(int),
    );
    yield r'kind';
    yield serializers.serialize(
      object.kind,
      specifiedType: const FullType(KindE0dEnum),
    );
    yield r'project_id';
    yield object.projectId == null
        ? null
        : serializers.serialize(
            object.projectId,
            specifiedType: const FullType.nullable(String),
          );
    yield r'scopes';
    yield object.scopes == null
        ? null
        : serializers.serialize(
            object.scopes,
            specifiedType: const FullType.nullable(JsonObject),
          );
    yield r'expires_at';
    yield object.expiresAt == null
        ? null
        : serializers.serialize(
            object.expiresAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'token';
    yield serializers.serialize(
      object.token,
      specifiedType: const FullType(String),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    AgentTokenIssueResponse object, {
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
    required AgentTokenIssueResponseBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.id = valueDes;
          break;
        case r'kind':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(KindE0dEnum),
          ) as KindE0dEnum;
          result.kind = valueDes;
          break;
        case r'project_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.projectId = valueDes;
          break;
        case r'scopes':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(JsonObject),
          ) as JsonObject?;
          if (valueDes == null) continue;
          result.scopes = valueDes;
          break;
        case r'expires_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.expiresAt = valueDes;
          break;
        case r'token':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.token = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AgentTokenIssueResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AgentTokenIssueResponseBuilder();
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
