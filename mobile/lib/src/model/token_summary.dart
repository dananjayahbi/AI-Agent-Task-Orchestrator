//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/kind_enum.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'token_summary.g.dart';

/// List item metadata — deliberately without ``hash`` (FR-SEC-04).
///
/// Properties:
/// * [id]
/// * [kind]
/// * [projectId]
/// * [scopes]
/// * [expiresAt]
/// * [revokedAt]
/// * [lastUsedAt]
@BuiltValue()
abstract class TokenSummary
    implements Built<TokenSummary, TokenSummaryBuilder> {
  @BuiltValueField(wireName: r'id')
  int get id;

  @BuiltValueField(wireName: r'kind')
  KindEnum get kind;
  // enum kindEnum {  owner_session,  agent,  device,  };

  @BuiltValueField(wireName: r'project_id')
  String? get projectId;

  @BuiltValueField(wireName: r'scopes')
  JsonObject? get scopes;

  @BuiltValueField(wireName: r'expires_at')
  DateTime? get expiresAt;

  @BuiltValueField(wireName: r'revoked_at')
  DateTime? get revokedAt;

  @BuiltValueField(wireName: r'last_used_at')
  DateTime? get lastUsedAt;

  TokenSummary._();

  factory TokenSummary([void updates(TokenSummaryBuilder b)]) = _$TokenSummary;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(TokenSummaryBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<TokenSummary> get serializer => _$TokenSummarySerializer();
}

class _$TokenSummarySerializer implements PrimitiveSerializer<TokenSummary> {
  @override
  final Iterable<Type> types = const [TokenSummary, _$TokenSummary];

  @override
  final String wireName = r'TokenSummary';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    TokenSummary object, {
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
      specifiedType: const FullType(KindEnum),
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
    yield r'revoked_at';
    yield object.revokedAt == null
        ? null
        : serializers.serialize(
            object.revokedAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'last_used_at';
    yield object.lastUsedAt == null
        ? null
        : serializers.serialize(
            object.lastUsedAt,
            specifiedType: const FullType.nullable(DateTime),
          );
  }

  @override
  Object serialize(
    Serializers serializers,
    TokenSummary object, {
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
    required TokenSummaryBuilder result,
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
            specifiedType: const FullType(KindEnum),
          ) as KindEnum;
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
        case r'revoked_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.revokedAt = valueDes;
          break;
        case r'last_used_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.lastUsedAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  TokenSummary deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = TokenSummaryBuilder();
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
