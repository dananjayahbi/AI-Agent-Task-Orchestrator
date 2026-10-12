//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/checkpoint.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'checkpoint_write_response.g.dart';

/// MT-1.8-03's frozen response — Section 10.5 \"Returns new expiry\".
///
/// Properties:
/// * [checkpoint] - The stored row's identity and Section 7.2 fields.
/// * [leaseExtended] - False for a kind that does not extend under the project's lease_extension_mode (OQ-04 recorded reading).
/// * [leaseExpiresAt] - The Section 8.6 deadline after this call — the new expiry the bridge turns into its next_checkpoint_due hint.
/// * [capped] - True when the hard cap clamped the extension — the owner must submit or release (MT-1.6-03's flag, consumed here).
@BuiltValue()
abstract class CheckpointWriteResponse
    implements Built<CheckpointWriteResponse, CheckpointWriteResponseBuilder> {
  /// The stored row's identity and Section 7.2 fields.
  @BuiltValueField(wireName: r'checkpoint')
  Checkpoint get checkpoint;

  /// False for a kind that does not extend under the project's lease_extension_mode (OQ-04 recorded reading).
  @BuiltValueField(wireName: r'lease_extended')
  bool get leaseExtended;

  /// The Section 8.6 deadline after this call — the new expiry the bridge turns into its next_checkpoint_due hint.
  @BuiltValueField(wireName: r'lease_expires_at')
  DateTime? get leaseExpiresAt;

  /// True when the hard cap clamped the extension — the owner must submit or release (MT-1.6-03's flag, consumed here).
  @BuiltValueField(wireName: r'capped')
  bool get capped;

  CheckpointWriteResponse._();

  factory CheckpointWriteResponse(
          [void updates(CheckpointWriteResponseBuilder b)]) =
      _$CheckpointWriteResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(CheckpointWriteResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<CheckpointWriteResponse> get serializer =>
      _$CheckpointWriteResponseSerializer();
}

class _$CheckpointWriteResponseSerializer
    implements PrimitiveSerializer<CheckpointWriteResponse> {
  @override
  final Iterable<Type> types = const [
    CheckpointWriteResponse,
    _$CheckpointWriteResponse
  ];

  @override
  final String wireName = r'CheckpointWriteResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    CheckpointWriteResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'checkpoint';
    yield serializers.serialize(
      object.checkpoint,
      specifiedType: const FullType(Checkpoint),
    );
    yield r'lease_extended';
    yield serializers.serialize(
      object.leaseExtended,
      specifiedType: const FullType(bool),
    );
    yield r'lease_expires_at';
    yield object.leaseExpiresAt == null
        ? null
        : serializers.serialize(
            object.leaseExpiresAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'capped';
    yield serializers.serialize(
      object.capped,
      specifiedType: const FullType(bool),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    CheckpointWriteResponse object, {
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
    required CheckpointWriteResponseBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'checkpoint':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(Checkpoint),
          ) as Checkpoint;
          result.checkpoint.replace(valueDes);
          break;
        case r'lease_extended':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.leaseExtended = valueDes;
          break;
        case r'lease_expires_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.leaseExpiresAt = valueDes;
          break;
        case r'capped':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.capped = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  CheckpointWriteResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = CheckpointWriteResponseBuilder();
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
