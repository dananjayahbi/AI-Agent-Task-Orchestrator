//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'health_ready.g.dart';

/// Response body of GET /health/ready.
///
/// Properties:
/// * [status]
/// * [checks]
@BuiltValue()
abstract class HealthReady implements Built<HealthReady, HealthReadyBuilder> {
  @BuiltValueField(wireName: r'status')
  String get status;

  @BuiltValueField(wireName: r'checks')
  BuiltMap<String, String> get checks;

  HealthReady._();

  factory HealthReady([void updates(HealthReadyBuilder b)]) = _$HealthReady;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(HealthReadyBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<HealthReady> get serializer => _$HealthReadySerializer();
}

class _$HealthReadySerializer implements PrimitiveSerializer<HealthReady> {
  @override
  final Iterable<Type> types = const [HealthReady, _$HealthReady];

  @override
  final String wireName = r'HealthReady';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    HealthReady object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'status';
    yield serializers.serialize(
      object.status,
      specifiedType: const FullType(String),
    );
    yield r'checks';
    yield serializers.serialize(
      object.checks,
      specifiedType:
          const FullType(BuiltMap, [FullType(String), FullType(String)]),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    HealthReady object, {
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
    required HealthReadyBuilder result,
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
        case r'checks':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType(BuiltMap, [FullType(String), FullType(String)]),
          ) as BuiltMap<String, String>;
          result.checks.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  HealthReady deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = HealthReadyBuilder();
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
