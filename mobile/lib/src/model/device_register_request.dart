//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/platform_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'device_register_request.g.dart';

/// POST /devices body.
///
/// Properties:
/// * [platform] - Mobile platform: ios or android.  * `ios` - iOS * `android` - Android
/// * [pushToken] - APNs/FCM registration token for push dispatch (Section 9.8). Sensitive at rest (Section 12.4) — stored, never returned.
/// * [biometricBound] - Whether the client has enrolled the biometric gate for this device (Section 12.2; enforcement is client-side, M5).
@BuiltValue()
abstract class DeviceRegisterRequest
    implements Built<DeviceRegisterRequest, DeviceRegisterRequestBuilder> {
  /// Mobile platform: ios or android.  * `ios` - iOS * `android` - Android
  @BuiltValueField(wireName: r'platform')
  PlatformEnum get platform;
  // enum platformEnum {  ios,  android,  };

  /// APNs/FCM registration token for push dispatch (Section 9.8). Sensitive at rest (Section 12.4) — stored, never returned.
  @BuiltValueField(wireName: r'push_token')
  String get pushToken;

  /// Whether the client has enrolled the biometric gate for this device (Section 12.2; enforcement is client-side, M5).
  @BuiltValueField(wireName: r'biometric_bound')
  bool? get biometricBound;

  DeviceRegisterRequest._();

  factory DeviceRegisterRequest(
      [void updates(DeviceRegisterRequestBuilder b)]) = _$DeviceRegisterRequest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(DeviceRegisterRequestBuilder b) =>
      b..biometricBound = false;

  @BuiltValueSerializer(custom: true)
  static Serializer<DeviceRegisterRequest> get serializer =>
      _$DeviceRegisterRequestSerializer();
}

class _$DeviceRegisterRequestSerializer
    implements PrimitiveSerializer<DeviceRegisterRequest> {
  @override
  final Iterable<Type> types = const [
    DeviceRegisterRequest,
    _$DeviceRegisterRequest
  ];

  @override
  final String wireName = r'DeviceRegisterRequest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    DeviceRegisterRequest object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'platform';
    yield serializers.serialize(
      object.platform,
      specifiedType: const FullType(PlatformEnum),
    );
    yield r'push_token';
    yield serializers.serialize(
      object.pushToken,
      specifiedType: const FullType(String),
    );
    if (object.biometricBound != null) {
      yield r'biometric_bound';
      yield serializers.serialize(
        object.biometricBound,
        specifiedType: const FullType(bool),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    DeviceRegisterRequest object, {
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
    required DeviceRegisterRequestBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'platform':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(PlatformEnum),
          ) as PlatformEnum;
          result.platform = valueDes;
          break;
        case r'push_token':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.pushToken = valueDes;
          break;
        case r'biometric_bound':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(bool),
          ) as bool?;
          if (valueDes == null) continue;
          result.biometricBound = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  DeviceRegisterRequest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = DeviceRegisterRequestBuilder();
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
