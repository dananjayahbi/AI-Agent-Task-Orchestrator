//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'health_live.g.dart';

/// Response body of GET /health/live.
///
/// Properties:
/// * [status]
@BuiltValue()
abstract class HealthLive implements Built<HealthLive, HealthLiveBuilder> {
  @BuiltValueField(wireName: r'status')
  String get status;

  HealthLive._();

  factory HealthLive([void updates(HealthLiveBuilder b)]) = _$HealthLive;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(HealthLiveBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<HealthLive> get serializer => _$HealthLiveSerializer();
}

class _$HealthLiveSerializer implements PrimitiveSerializer<HealthLive> {
  @override
  final Iterable<Type> types = const [HealthLive, _$HealthLive];

  @override
  final String wireName = r'HealthLive';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    HealthLive object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'status';
    yield serializers.serialize(
      object.status,
      specifiedType: const FullType(String),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    HealthLive object, {
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
    required HealthLiveBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'status':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.status = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  HealthLive deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = HealthLiveBuilder();
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
