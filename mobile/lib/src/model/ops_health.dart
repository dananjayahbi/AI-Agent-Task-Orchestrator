//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'ops_health.g.dart';

/// Section 17 Health row: live plus the ready checks' reachability.
///
/// Properties:
/// * [live] - Always true in a 200 body — this process served the request.
/// * [checks] - 'database'/'cache' → 'ok' or 'unreachable' (same pings as /health/ready).
@BuiltValue()
abstract class OpsHealth implements Built<OpsHealth, OpsHealthBuilder> {
  /// Always true in a 200 body — this process served the request.
  @BuiltValueField(wireName: r'live')
  bool get live;

  /// 'database'/'cache' → 'ok' or 'unreachable' (same pings as /health/ready).
  @BuiltValueField(wireName: r'checks')
  BuiltMap<String, String> get checks;

  OpsHealth._();

  factory OpsHealth([void updates(OpsHealthBuilder b)]) = _$OpsHealth;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(OpsHealthBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<OpsHealth> get serializer => _$OpsHealthSerializer();
}

class _$OpsHealthSerializer implements PrimitiveSerializer<OpsHealth> {
  @override
  final Iterable<Type> types = const [OpsHealth, _$OpsHealth];

  @override
  final String wireName = r'OpsHealth';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    OpsHealth object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'live';
    yield serializers.serialize(
      object.live,
      specifiedType: const FullType(bool),
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
    OpsHealth object, {
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
    required OpsHealthBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'live':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.live = valueDes;
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
  OpsHealth deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = OpsHealthBuilder();
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
