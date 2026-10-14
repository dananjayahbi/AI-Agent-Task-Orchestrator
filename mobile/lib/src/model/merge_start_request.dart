//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'merge_start_request.g.dart';

/// ``POST /merge/{task}/start`` input — no required fields (claim is id-less).
///
/// Properties:
/// * [version] - Optional task ``version`` the executor saw in the listing (FR-TSK-06) — a stale value answers VERSION_CONFLICT (409) and claims nothing.
@BuiltValue()
abstract class MergeStartRequest
    implements Built<MergeStartRequest, MergeStartRequestBuilder> {
  /// Optional task ``version`` the executor saw in the listing (FR-TSK-06) — a stale value answers VERSION_CONFLICT (409) and claims nothing.
  @BuiltValueField(wireName: r'version')
  int? get version;

  MergeStartRequest._();

  factory MergeStartRequest([void updates(MergeStartRequestBuilder b)]) =
      _$MergeStartRequest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(MergeStartRequestBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<MergeStartRequest> get serializer =>
      _$MergeStartRequestSerializer();
}

class _$MergeStartRequestSerializer
    implements PrimitiveSerializer<MergeStartRequest> {
  @override
  final Iterable<Type> types = const [MergeStartRequest, _$MergeStartRequest];

  @override
  final String wireName = r'MergeStartRequest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    MergeStartRequest object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    if (object.version != null) {
      yield r'version';
      yield serializers.serialize(
        object.version,
        specifiedType: const FullType(int),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    MergeStartRequest object, {
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
    required MergeStartRequestBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'version':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.version = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  MergeStartRequest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = MergeStartRequestBuilder();
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
