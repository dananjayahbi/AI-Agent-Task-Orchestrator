//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/platform_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'device_summary.g.dart';

/// GET /devices list item — metadata only (Section 12.4; Section 7.2).  Deliberately without ``push_token`` (sensitive at rest) and without any token material: the credential's expiry is shown because settings needs it, the hash/plaintext never leave the server.
///
/// Properties:
/// * [id]
/// * [platform]
/// * [biometricBound]
/// * [lastSeenAt] - Last request authenticated with this device's token (Section 7.2).
/// * [revokedAt] - Revocation instant; null = still active (lost-phone control).
/// * [expiresAt] - Expiry of the device-bound token (Section 9.10 lifetime).
@BuiltValue()
abstract class DeviceSummary
    implements Built<DeviceSummary, DeviceSummaryBuilder> {
  @BuiltValueField(wireName: r'id')
  int get id;

  @BuiltValueField(wireName: r'platform')
  PlatformEnum get platform;
  // enum platformEnum {  ios,  android,  };

  @BuiltValueField(wireName: r'biometric_bound')
  bool get biometricBound;

  /// Last request authenticated with this device's token (Section 7.2).
  @BuiltValueField(wireName: r'last_seen_at')
  DateTime? get lastSeenAt;

  /// Revocation instant; null = still active (lost-phone control).
  @BuiltValueField(wireName: r'revoked_at')
  DateTime? get revokedAt;

  /// Expiry of the device-bound token (Section 9.10 lifetime).
  @BuiltValueField(wireName: r'expires_at')
  DateTime? get expiresAt;

  DeviceSummary._();

  factory DeviceSummary([void updates(DeviceSummaryBuilder b)]) =
      _$DeviceSummary;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(DeviceSummaryBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<DeviceSummary> get serializer =>
      _$DeviceSummarySerializer();
}

class _$DeviceSummarySerializer implements PrimitiveSerializer<DeviceSummary> {
  @override
  final Iterable<Type> types = const [DeviceSummary, _$DeviceSummary];

  @override
  final String wireName = r'DeviceSummary';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    DeviceSummary object, {
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
    yield r'last_seen_at';
    yield object.lastSeenAt == null
        ? null
        : serializers.serialize(
            object.lastSeenAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'revoked_at';
    yield object.revokedAt == null
        ? null
        : serializers.serialize(
            object.revokedAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'expires_at';
    yield object.expiresAt == null
        ? null
        : serializers.serialize(
            object.expiresAt,
            specifiedType: const FullType.nullable(DateTime),
          );
  }

  @override
  Object serialize(
    Serializers serializers,
    DeviceSummary object, {
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
    required DeviceSummaryBuilder result,
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
        case r'last_seen_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.lastSeenAt = valueDes;
          break;
        case r'revoked_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.revokedAt = valueDes;
          break;
        case r'expires_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
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
  DeviceSummary deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = DeviceSummaryBuilder();
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
