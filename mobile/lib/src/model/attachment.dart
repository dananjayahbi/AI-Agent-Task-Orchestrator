//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'attachment.g.dart';

/// One attachment descriptor — FR-ATT-03's field shape, locked here.
///
/// Properties:
/// * [id] - Server-generated row identity (Section 7.2).
/// * [taskId] - The owning task (Section 7.2).
/// * [filename] - Client filename, path components stripped.
/// * [mimeType] - The sniffed content type (Section 9.5 — never the declared one).
/// * [size] - Stored size in bytes (Section 7.2 ``size_bytes``).
/// * [isImage] - Whether the sniffed type is an image — drives the pipeline split (9.5).
/// * [processingStatus] - FR-ATT-07 enum: uploaded | processing | ready | failed.
/// * [tokenCount] - FR-ATT-03 token count — null until the WP-1.12 pipeline computes it.
/// * [shortDescription] - FR-ATT-03 short description — null until the WP-1.12 pipeline produces it.
/// * [createdAt] - Server upload time (P7).
@BuiltValue()
abstract class Attachment implements Built<Attachment, AttachmentBuilder> {
  /// Server-generated row identity (Section 7.2).
  @BuiltValueField(wireName: r'id')
  String get id;

  /// The owning task (Section 7.2).
  @BuiltValueField(wireName: r'task_id')
  String get taskId;

  /// Client filename, path components stripped.
  @BuiltValueField(wireName: r'filename')
  String get filename;

  /// The sniffed content type (Section 9.5 — never the declared one).
  @BuiltValueField(wireName: r'mime_type')
  String get mimeType;

  /// Stored size in bytes (Section 7.2 ``size_bytes``).
  @BuiltValueField(wireName: r'size')
  int get size;

  /// Whether the sniffed type is an image — drives the pipeline split (9.5).
  @BuiltValueField(wireName: r'is_image')
  bool get isImage;

  /// FR-ATT-07 enum: uploaded | processing | ready | failed.
  @BuiltValueField(wireName: r'processing_status')
  String get processingStatus;

  /// FR-ATT-03 token count — null until the WP-1.12 pipeline computes it.
  @BuiltValueField(wireName: r'token_count')
  int? get tokenCount;

  /// FR-ATT-03 short description — null until the WP-1.12 pipeline produces it.
  @BuiltValueField(wireName: r'short_description')
  String? get shortDescription;

  /// Server upload time (P7).
  @BuiltValueField(wireName: r'created_at')
  DateTime get createdAt;

  Attachment._();

  factory Attachment([void updates(AttachmentBuilder b)]) = _$Attachment;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AttachmentBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<Attachment> get serializer => _$AttachmentSerializer();
}

class _$AttachmentSerializer implements PrimitiveSerializer<Attachment> {
  @override
  final Iterable<Type> types = const [Attachment, _$Attachment];

  @override
  final String wireName = r'Attachment';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    Attachment object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'task_id';
    yield serializers.serialize(
      object.taskId,
      specifiedType: const FullType(String),
    );
    yield r'filename';
    yield serializers.serialize(
      object.filename,
      specifiedType: const FullType(String),
    );
    yield r'mime_type';
    yield serializers.serialize(
      object.mimeType,
      specifiedType: const FullType(String),
    );
    yield r'size';
    yield serializers.serialize(
      object.size,
      specifiedType: const FullType(int),
    );
    yield r'is_image';
    yield serializers.serialize(
      object.isImage,
      specifiedType: const FullType(bool),
    );
    yield r'processing_status';
    yield serializers.serialize(
      object.processingStatus,
      specifiedType: const FullType(String),
    );
    yield r'token_count';
    yield object.tokenCount == null
        ? null
        : serializers.serialize(
            object.tokenCount,
            specifiedType: const FullType.nullable(int),
          );
    yield r'short_description';
    yield object.shortDescription == null
        ? null
        : serializers.serialize(
            object.shortDescription,
            specifiedType: const FullType.nullable(String),
          );
    yield r'created_at';
    yield serializers.serialize(
      object.createdAt,
      specifiedType: const FullType(DateTime),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    Attachment object, {
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
    required AttachmentBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.id = valueDes;
          break;
        case r'task_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.taskId = valueDes;
          break;
        case r'filename':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.filename = valueDes;
          break;
        case r'mime_type':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.mimeType = valueDes;
          break;
        case r'size':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.size = valueDes;
          break;
        case r'is_image':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.isImage = valueDes;
          break;
        case r'processing_status':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.processingStatus = valueDes;
          break;
        case r'token_count':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.tokenCount = valueDes;
          break;
        case r'short_description':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.shortDescription = valueDes;
          break;
        case r'created_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.createdAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  Attachment deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AttachmentBuilder();
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
