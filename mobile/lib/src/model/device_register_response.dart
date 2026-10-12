//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/platform_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'device_register_response.g.dart';

/// POST /devices 201 body: metadata + the token shown exactly once.
///
/// Properties:
/// * [id]
/// * [platform]
/// * [biometricBound]
/// * [expiresAt]
/// * [token] - The device-bound plaintext token — returned exactly once, now; store it in platform secure storage. The server keeps only its SHA-256 hash (Section 7.2) and cannot show it again.
@BuiltValue()
abstract class DeviceRegisterResponse
    implements Built<DeviceRegisterResponse, DeviceRegisterResponseBuilder> {
  @BuiltValueField(wireName: r'id')
  int get id;

  @BuiltValueField(wireName: r'platform')
  PlatformEnum get platform;
  // enum platformEnum {  ios,  android,  };

  @BuiltValueField(wireName: r'biometric_bound')
  bool get biometricBound;

  @BuiltValueField(wireName: r'expires_at')
  DateTime get expiresAt;

  /// The device-bound plaintext token — returned exactly once, now; store it in platform secure storage. The server keeps only its SHA-256 hash (Section 7.2) and cannot show it again.
  @BuiltValueField(wireName: r'token')
  String get token;

  DeviceRegisterResponse._();

  factory DeviceRegisterResponse(
          [void updates(DeviceRegisterResponseBuilder b)]) =
      _$DeviceRegisterResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(DeviceRegisterResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<DeviceRegisterResponse> get serializer =>
      _$DeviceRegisterResponseSerializer();
}

class _$DeviceRegisterResponseSerializer
    implements PrimitiveSerializer<DeviceRegisterResponse> {
  @override
  final Iterable<Type> types = const [
    DeviceRegisterResponse,
    _$DeviceRegisterResponse
  ];

  @override
  final String wireName = r'DeviceRegisterResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    DeviceRegisterResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(int),
    );
    yield r'platform';
    yield serializers.serialize(
      object.platform,
      specifiedType: const FullType(PlatformEnum),
    );
    yield r'biometric_bound';
    yield serializers.serialize(
      object.biometricBound,
      specifiedType: const FullType(bool),
    );
    yield r'expires_at';
    yield serializers.serialize(
      object.expiresAt,
      specifiedType: const FullType(DateTime),
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
    DeviceRegisterResponse object, {
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
    required DeviceRegisterResponseBuilder result,
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
        case r'platform':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(PlatformEnum),
          ) as PlatformEnum;
          result.platform = valueDes;
          break;
        case r'biometric_bound':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.biometricBound = valueDes;
          break;
        case r'expires_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
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
  DeviceRegisterResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = DeviceRegisterResponseBuilder();
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
