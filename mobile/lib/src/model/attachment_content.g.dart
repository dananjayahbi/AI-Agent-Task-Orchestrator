// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'attachment_content.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AttachmentContent extends AttachmentContent {
  @override
  final String attachmentId;
  @override
  final String format;
  @override
  final String? content;
  @override
  final String? description;
  @override
  final String? imageBase64;
  @override
  final String? mediaType;
  @override
  final int? pageNumber;
  @override
  final int? totalPages;
  @override
  final int? tokenCount;

  factory _$AttachmentContent(
          [void Function(AttachmentContentBuilder)? updates]) =>
      (AttachmentContentBuilder()..update(updates))._build();

  _$AttachmentContent._(
      {required this.attachmentId,
      required this.format,
      this.content,
      this.description,
      this.imageBase64,
      this.mediaType,
      this.pageNumber,
      this.totalPages,
      this.tokenCount})
      : super._();
  @override
  AttachmentContent rebuild(void Function(AttachmentContentBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AttachmentContentBuilder toBuilder() =>
      AttachmentContentBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AttachmentContent &&
        attachmentId == other.attachmentId &&
        format == other.format &&
        content == other.content &&
        description == other.description &&
        imageBase64 == other.imageBase64 &&
        mediaType == other.mediaType &&
        pageNumber == other.pageNumber &&
        totalPages == other.totalPages &&
        tokenCount == other.tokenCount;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, attachmentId.hashCode);
    _$hash = $jc(_$hash, format.hashCode);
    _$hash = $jc(_$hash, content.hashCode);
    _$hash = $jc(_$hash, description.hashCode);
    _$hash = $jc(_$hash, imageBase64.hashCode);
    _$hash = $jc(_$hash, mediaType.hashCode);
    _$hash = $jc(_$hash, pageNumber.hashCode);
    _$hash = $jc(_$hash, totalPages.hashCode);
    _$hash = $jc(_$hash, tokenCount.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AttachmentContent')
          ..add('attachmentId', attachmentId)
          ..add('format', format)
          ..add('content', content)
          ..add('description', description)
          ..add('imageBase64', imageBase64)
          ..add('mediaType', mediaType)
          ..add('pageNumber', pageNumber)
          ..add('totalPages', totalPages)
          ..add('tokenCount', tokenCount))
        .toString();
  }
}

class AttachmentContentBuilder
    implements Builder<AttachmentContent, AttachmentContentBuilder> {
  _$AttachmentContent? _$v;

  String? _attachmentId;
  String? get attachmentId => _$this._attachmentId;
  set attachmentId(String? attachmentId) => _$this._attachmentId = attachmentId;

  String? _format;
  String? get format => _$this._format;
  set format(String? format) => _$this._format = format;

  String? _content;
  String? get content => _$this._content;
  set content(String? content) => _$this._content = content;

  String? _description;
  String? get description => _$this._description;
  set description(String? description) => _$this._description = description;

  String? _imageBase64;
  String? get imageBase64 => _$this._imageBase64;
  set imageBase64(String? imageBase64) => _$this._imageBase64 = imageBase64;

  String? _mediaType;
  String? get mediaType => _$this._mediaType;
  set mediaType(String? mediaType) => _$this._mediaType = mediaType;

  int? _pageNumber;
  int? get pageNumber => _$this._pageNumber;
  set pageNumber(int? pageNumber) => _$this._pageNumber = pageNumber;

  int? _totalPages;
  int? get totalPages => _$this._totalPages;
  set totalPages(int? totalPages) => _$this._totalPages = totalPages;

  int? _tokenCount;
  int? get tokenCount => _$this._tokenCount;
  set tokenCount(int? tokenCount) => _$this._tokenCount = tokenCount;

  AttachmentContentBuilder() {
    AttachmentContent._defaults(this);
  }

  AttachmentContentBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _attachmentId = $v.attachmentId;
      _format = $v.format;
      _content = $v.content;
      _description = $v.description;
      _imageBase64 = $v.imageBase64;
      _mediaType = $v.mediaType;
      _pageNumber = $v.pageNumber;
      _totalPages = $v.totalPages;
      _tokenCount = $v.tokenCount;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AttachmentContent other) {
    _$v = other as _$AttachmentContent;
  }

  @override
  void update(void Function(AttachmentContentBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AttachmentContent build() => _build();

  _$AttachmentContent _build() {
    final _$result = _$v ??
        _$AttachmentContent._(
          attachmentId: BuiltValueNullFieldError.checkNotNull(
              attachmentId, r'AttachmentContent', 'attachmentId'),
          format: BuiltValueNullFieldError.checkNotNull(
              format, r'AttachmentContent', 'format'),
          content: content,
          description: description,
          imageBase64: imageBase64,
          mediaType: mediaType,
          pageNumber: pageNumber,
          totalPages: totalPages,
          tokenCount: tokenCount,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
