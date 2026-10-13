//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'attachment_content.g.dart';

/// The content endpoint's 200 body (Section 9.5 retrieval behavior).
///
/// Properties:
/// * [attachmentId] - The addressed attachment (Section 7.2).
/// * [format] - The resolved concrete format — `auto` never reaches the wire.
/// * [content] - The delivered text (markdown page or OCR transcript), prefixed with the untrusted-content banner (P10; Section 9.5). Null for image_base64.
/// * [description] - text_ocr only: the layout description, banner-prefixed (P10); empty after OCR-only degradation (MT-1.13-05); null for other formats.
/// * [imageBase64] - image_base64 only: the normalized image (Section 9.5 stage 2).
/// * [mediaType] - image_base64 only: the normalized image's media type (always image/png).
/// * [pageNumber] - Paginated responses only: this page's one-based number (Section 9.5).
/// * [totalPages] - Paginated responses only: total pages — 1 for a single-page document (MT-1.14-03 convention).
/// * [tokenCount] - Paginated responses only: this page's token estimate (as stored by WP-1.12) so an agent can budget context (9.5).
@BuiltValue()
abstract class AttachmentContent
    implements Built<AttachmentContent, AttachmentContentBuilder> {
  /// The addressed attachment (Section 7.2).
  @BuiltValueField(wireName: r'attachment_id')
  String get attachmentId;

  /// The resolved concrete format — `auto` never reaches the wire.
  @BuiltValueField(wireName: r'format')
  String get format;

  /// The delivered text (markdown page or OCR transcript), prefixed with the untrusted-content banner (P10; Section 9.5). Null for image_base64.
  @BuiltValueField(wireName: r'content')
  String? get content;

  /// text_ocr only: the layout description, banner-prefixed (P10); empty after OCR-only degradation (MT-1.13-05); null for other formats.
  @BuiltValueField(wireName: r'description')
  String? get description;

  /// image_base64 only: the normalized image (Section 9.5 stage 2).
  @BuiltValueField(wireName: r'image_base64')
  String? get imageBase64;

  /// image_base64 only: the normalized image's media type (always image/png).
  @BuiltValueField(wireName: r'media_type')
  String? get mediaType;

  /// Paginated responses only: this page's one-based number (Section 9.5).
  @BuiltValueField(wireName: r'page_number')
  int? get pageNumber;

  /// Paginated responses only: total pages — 1 for a single-page document (MT-1.14-03 convention).
  @BuiltValueField(wireName: r'total_pages')
  int? get totalPages;

  /// Paginated responses only: this page's token estimate (as stored by WP-1.12) so an agent can budget context (9.5).
  @BuiltValueField(wireName: r'token_count')
  int? get tokenCount;

  AttachmentContent._();

  factory AttachmentContent([void updates(AttachmentContentBuilder b)]) =
      _$AttachmentContent;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AttachmentContentBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AttachmentContent> get serializer =>
      _$AttachmentContentSerializer();
}

class _$AttachmentContentSerializer
    implements PrimitiveSerializer<AttachmentContent> {
  @override
  final Iterable<Type> types = const [AttachmentContent, _$AttachmentContent];

  @override
  final String wireName = r'AttachmentContent';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AttachmentContent object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'attachment_id';
    yield serializers.serialize(
      object.attachmentId,
      specifiedType: const FullType(String),
    );
    yield r'format';
    yield serializers.serialize(
      object.format,
      specifiedType: const FullType(String),
    );
    yield r'content';
    yield object.content == null
        ? null
        : serializers.serialize(
            object.content,
            specifiedType: const FullType.nullable(String),
          );
    yield r'description';
    yield object.description == null
        ? null
        : serializers.serialize(
            object.description,
            specifiedType: const FullType.nullable(String),
          );
    yield r'image_base64';
    yield object.imageBase64 == null
        ? null
        : serializers.serialize(
            object.imageBase64,
            specifiedType: const FullType.nullable(String),
          );
    yield r'media_type';
    yield object.mediaType == null
        ? null
        : serializers.serialize(
            object.mediaType,
            specifiedType: const FullType.nullable(String),
          );
    yield r'page_number';
    yield object.pageNumber == null
        ? null
        : serializers.serialize(
            object.pageNumber,
            specifiedType: const FullType.nullable(int),
          );
    yield r'total_pages';
    yield object.totalPages == null
        ? null
        : serializers.serialize(
            object.totalPages,
            specifiedType: const FullType.nullable(int),
          );
    yield r'token_count';
    yield object.tokenCount == null
        ? null
        : serializers.serialize(
            object.tokenCount,
            specifiedType: const FullType.nullable(int),
          );
  }

  @override
  Object serialize(
    Serializers serializers,
    AttachmentContent object, {
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
    required AttachmentContentBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'attachment_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.attachmentId = valueDes;
          break;
        case r'format':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.format = valueDes;
          break;
        case r'content':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.content = valueDes;
          break;
        case r'description':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.description = valueDes;
          break;
        case r'image_base64':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.imageBase64 = valueDes;
          break;
        case r'media_type':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.mediaType = valueDes;
          break;
        case r'page_number':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.pageNumber = valueDes;
          break;
        case r'total_pages':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.totalPages = valueDes;
          break;
        case r'token_count':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.tokenCount = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AttachmentContent deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AttachmentContentBuilder();
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
