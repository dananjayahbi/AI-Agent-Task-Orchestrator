//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'revoked.g.dart';

/// POST /auth/logout: the instant the session token stopped working.
///
/// Properties:
/// * [revokedAt]
@BuiltValue()
abstract class Revoked implements Built<Revoked, RevokedBuilder> {
  @BuiltValueField(wireName: r'revoked_at')
  DateTime get revokedAt;

  Revoked._();

  factory Revoked([void updates(RevokedBuilder b)]) = _$Revoked;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(RevokedBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<Revoked> get serializer => _$RevokedSerializer();
}

class _$RevokedSerializer implements PrimitiveSerializer<Revoked> {
  @override
  final Iterable<Type> types = const [Revoked, _$Revoked];

  @override
  final String wireName = r'Revoked';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    Revoked object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'revoked_at';
    yield serializers.serialize(
      object.revokedAt,
      specifiedType: const FullType(DateTime),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    Revoked object, {
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
    required RevokedBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'revoked_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.revokedAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  Revoked deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = RevokedBuilder();
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
