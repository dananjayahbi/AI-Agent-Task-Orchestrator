//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'resolution_patch.g.dart';

/// ``GET /resolutions/{id}/patch`` body — one shape, both paths (9.2).
///
/// Properties:
/// * [resolutionId]
/// * [kind] - Artifact kind (Section 7.2): patch.
/// * [sha256] - Server-computed SHA-256 of the patch bytes (Section 7.2; 9.7).
/// * [sizeBytes] - Server-computed size in bytes (Section 7.2) — compared against the Section 9.7 5 MB cap (inclusive) for diff_too_large.
/// * [diffTooLarge] - True when the patch exceeded the 5 MB cap and only stats/file list were kept (Section 9.7's degraded path).
/// * [patch_] - The stored unified patch, or null on the oversize path (9.7).
/// * [marker] - Literal viewers render on the oversize path: 'diff too large' (Section 9.7; null when the body is served).
@BuiltValue()
abstract class ResolutionPatch
    implements Built<ResolutionPatch, ResolutionPatchBuilder> {
  @BuiltValueField(wireName: r'resolution_id')
  String get resolutionId;

  /// Artifact kind (Section 7.2): patch.
  @BuiltValueField(wireName: r'kind')
  String get kind;

  /// Server-computed SHA-256 of the patch bytes (Section 7.2; 9.7).
  @BuiltValueField(wireName: r'sha256')
  String get sha256;

  /// Server-computed size in bytes (Section 7.2) — compared against the Section 9.7 5 MB cap (inclusive) for diff_too_large.
  @BuiltValueField(wireName: r'size_bytes')
  int get sizeBytes;

  /// True when the patch exceeded the 5 MB cap and only stats/file list were kept (Section 9.7's degraded path).
  @BuiltValueField(wireName: r'diff_too_large')
  bool get diffTooLarge;

  /// The stored unified patch, or null on the oversize path (9.7).
  @BuiltValueField(wireName: r'patch')
  String? get patch_;

  /// Literal viewers render on the oversize path: 'diff too large' (Section 9.7; null when the body is served).
  @BuiltValueField(wireName: r'marker')
  String? get marker;

  ResolutionPatch._();

  factory ResolutionPatch([void updates(ResolutionPatchBuilder b)]) =
      _$ResolutionPatch;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ResolutionPatchBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<ResolutionPatch> get serializer =>
      _$ResolutionPatchSerializer();
}

class _$ResolutionPatchSerializer
    implements PrimitiveSerializer<ResolutionPatch> {
  @override
  final Iterable<Type> types = const [ResolutionPatch, _$ResolutionPatch];

  @override
  final String wireName = r'ResolutionPatch';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ResolutionPatch object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'resolution_id';
    yield serializers.serialize(
      object.resolutionId,
      specifiedType: const FullType(String),
    );
    yield r'kind';
    yield serializers.serialize(
      object.kind,
      specifiedType: const FullType(String),
    );
    yield r'sha256';
    yield serializers.serialize(
      object.sha256,
      specifiedType: const FullType(String),
    );
    yield r'size_bytes';
    yield serializers.serialize(
      object.sizeBytes,
      specifiedType: const FullType(int),
    );
    yield r'diff_too_large';
    yield serializers.serialize(
      object.diffTooLarge,
      specifiedType: const FullType(bool),
    );
    yield r'patch';
    yield object.patch_ == null
        ? null
        : serializers.serialize(
            object.patch_,
            specifiedType: const FullType.nullable(String),
          );
    yield r'marker';
    yield object.marker == null
        ? null
        : serializers.serialize(
            object.marker,
            specifiedType: const FullType.nullable(String),
          );
  }

  @override
  Object serialize(
    Serializers serializers,
    ResolutionPatch object, {
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
    required ResolutionPatchBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'resolution_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.resolutionId = valueDes;
          break;
        case r'kind':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.kind = valueDes;
          break;
        case r'sha256':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.sha256 = valueDes;
          break;
        case r'size_bytes':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.sizeBytes = valueDes;
          break;
        case r'diff_too_large':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.diffTooLarge = valueDes;
          break;
        case r'patch':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.patch_ = valueDes;
          break;
        case r'marker':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.marker = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ResolutionPatch deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ResolutionPatchBuilder();
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
