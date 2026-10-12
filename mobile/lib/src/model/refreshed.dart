//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'refreshed.g.dart';

/// POST /auth/refresh: the extended expiry (same lifetime settings).
///
/// Properties:
/// * [expiresAt]
@BuiltValue()
abstract class Refreshed implements Built<Refreshed, RefreshedBuilder> {
  @BuiltValueField(wireName: r'expires_at')
  DateTime get expiresAt;

  Refreshed._();

  factory Refreshed([void updates(RefreshedBuilder b)]) = _$Refreshed;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(RefreshedBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<Refreshed> get serializer => _$RefreshedSerializer();
}

class _$RefreshedSerializer implements PrimitiveSerializer<Refreshed> {
  @override
  final Iterable<Type> types = const [Refreshed, _$Refreshed];

  @override
  final String wireName = r'Refreshed';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    Refreshed object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'expires_at';
    yield serializers.serialize(
      object.expiresAt,
      specifiedType: const FullType(DateTime),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    Refreshed object, {
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
    required RefreshedBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'expires_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.expiresAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  Refreshed deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = RefreshedBuilder();
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
