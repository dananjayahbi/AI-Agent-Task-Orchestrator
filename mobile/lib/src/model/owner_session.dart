//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/user_summary.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'owner_session.g.dart';

/// The login payload: plaintext binding once + row expiry + identity.
///
/// Properties:
/// * [token] - The owner session token. Returned exactly once at login; the server stores only its SHA-256 hash (Section 7.2). Web clients rely on the session cookie and may ignore it; token-auth clients (Section 15.4) send it as `Authorization: Bearer <token>`.
/// * [expiresAt]
/// * [user]
@BuiltValue()
abstract class OwnerSession
    implements Built<OwnerSession, OwnerSessionBuilder> {
  /// The owner session token. Returned exactly once at login; the server stores only its SHA-256 hash (Section 7.2). Web clients rely on the session cookie and may ignore it; token-auth clients (Section 15.4) send it as `Authorization: Bearer <token>`.
  @BuiltValueField(wireName: r'token')
  String get token;

  @BuiltValueField(wireName: r'expires_at')
  DateTime get expiresAt;

  @BuiltValueField(wireName: r'user')
  UserSummary get user;

  OwnerSession._();

  factory OwnerSession([void updates(OwnerSessionBuilder b)]) = _$OwnerSession;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(OwnerSessionBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<OwnerSession> get serializer => _$OwnerSessionSerializer();
}

class _$OwnerSessionSerializer implements PrimitiveSerializer<OwnerSession> {
  @override
  final Iterable<Type> types = const [OwnerSession, _$OwnerSession];

  @override
  final String wireName = r'OwnerSession';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    OwnerSession object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'token';
    yield serializers.serialize(
      object.token,
      specifiedType: const FullType(String),
    );
    yield r'expires_at';
    yield serializers.serialize(
      object.expiresAt,
      specifiedType: const FullType(DateTime),
    );
    yield r'user';
    yield serializers.serialize(
      object.user,
      specifiedType: const FullType(UserSummary),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    OwnerSession object, {
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
    required OwnerSessionBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'token':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.token = valueDes;
          break;
        case r'expires_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.expiresAt = valueDes;
          break;
        case r'user':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(UserSummary),
          ) as UserSummary;
          result.user.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  OwnerSession deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = OwnerSessionBuilder();
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
