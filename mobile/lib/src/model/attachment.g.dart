// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'attachment.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$Attachment extends Attachment {
  @override
  final String id;
  @override
  final String taskId;
  @override
  final String filename;
  @override
  final String mimeType;
  @override
  final int size;
  @override
  final bool isImage;
  @override
  final String processingStatus;
  @override
  final String? failureReason;
  @override
  final int? tokenCount;
  @override
  final String? shortDescription;
  @override
  final DateTime createdAt;

  factory _$Attachment([void Function(AttachmentBuilder)? updates]) =>
      (AttachmentBuilder()..update(updates))._build();

  _$Attachment._(
      {required this.id,
      required this.taskId,
      required this.filename,
      required this.mimeType,
      required this.size,
      required this.isImage,
      required this.processingStatus,
      this.failureReason,
      this.tokenCount,
      this.shortDescription,
      required this.createdAt})
      : super._();
  @override
  Attachment rebuild(void Function(AttachmentBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AttachmentBuilder toBuilder() => AttachmentBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is Attachment &&
        id == other.id &&
        taskId == other.taskId &&
        filename == other.filename &&
        mimeType == other.mimeType &&
        size == other.size &&
        isImage == other.isImage &&
        processingStatus == other.processingStatus &&
        failureReason == other.failureReason &&
        tokenCount == other.tokenCount &&
        shortDescription == other.shortDescription &&
        createdAt == other.createdAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, taskId.hashCode);
    _$hash = $jc(_$hash, filename.hashCode);
    _$hash = $jc(_$hash, mimeType.hashCode);
    _$hash = $jc(_$hash, size.hashCode);
    _$hash = $jc(_$hash, isImage.hashCode);
    _$hash = $jc(_$hash, processingStatus.hashCode);
    _$hash = $jc(_$hash, failureReason.hashCode);
    _$hash = $jc(_$hash, tokenCount.hashCode);
    _$hash = $jc(_$hash, shortDescription.hashCode);
    _$hash = $jc(_$hash, createdAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'Attachment')
          ..add('id', id)
          ..add('taskId', taskId)
          ..add('filename', filename)
          ..add('mimeType', mimeType)
          ..add('size', size)
          ..add('isImage', isImage)
          ..add('processingStatus', processingStatus)
          ..add('failureReason', failureReason)
          ..add('tokenCount', tokenCount)
          ..add('shortDescription', shortDescription)
          ..add('createdAt', createdAt))
        .toString();
  }
}

class AttachmentBuilder implements Builder<Attachment, AttachmentBuilder> {
  _$Attachment? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _taskId;
  String? get taskId => _$this._taskId;
  set taskId(String? taskId) => _$this._taskId = taskId;

  String? _filename;
  String? get filename => _$this._filename;
  set filename(String? filename) => _$this._filename = filename;

  String? _mimeType;
  String? get mimeType => _$this._mimeType;
  set mimeType(String? mimeType) => _$this._mimeType = mimeType;

  int? _size;
  int? get size => _$this._size;
  set size(int? size) => _$this._size = size;

  bool? _isImage;
  bool? get isImage => _$this._isImage;
  set isImage(bool? isImage) => _$this._isImage = isImage;

  String? _processingStatus;
  String? get processingStatus => _$this._processingStatus;
  set processingStatus(String? processingStatus) =>
      _$this._processingStatus = processingStatus;

  String? _failureReason;
  String? get failureReason => _$this._failureReason;
  set failureReason(String? failureReason) =>
      _$this._failureReason = failureReason;

  int? _tokenCount;
  int? get tokenCount => _$this._tokenCount;
  set tokenCount(int? tokenCount) => _$this._tokenCount = tokenCount;

  String? _shortDescription;
  String? get shortDescription => _$this._shortDescription;
  set shortDescription(String? shortDescription) =>
      _$this._shortDescription = shortDescription;

  DateTime? _createdAt;
  DateTime? get createdAt => _$this._createdAt;
  set createdAt(DateTime? createdAt) => _$this._createdAt = createdAt;

  AttachmentBuilder() {
    Attachment._defaults(this);
  }

  AttachmentBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _taskId = $v.taskId;
      _filename = $v.filename;
      _mimeType = $v.mimeType;
      _size = $v.size;
      _isImage = $v.isImage;
      _processingStatus = $v.processingStatus;
      _failureReason = $v.failureReason;
      _tokenCount = $v.tokenCount;
      _shortDescription = $v.shortDescription;
      _createdAt = $v.createdAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(Attachment other) {
    _$v = other as _$Attachment;
  }

  @override
  void update(void Function(AttachmentBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  Attachment build() => _build();

  _$Attachment _build() {
    final _$result = _$v ??
        _$Attachment._(
          id: BuiltValueNullFieldError.checkNotNull(id, r'Attachment', 'id'),
          taskId: BuiltValueNullFieldError.checkNotNull(
              taskId, r'Attachment', 'taskId'),
          filename: BuiltValueNullFieldError.checkNotNull(
              filename, r'Attachment', 'filename'),
          mimeType: BuiltValueNullFieldError.checkNotNull(
              mimeType, r'Attachment', 'mimeType'),
          size: BuiltValueNullFieldError.checkNotNull(
              size, r'Attachment', 'size'),
          isImage: BuiltValueNullFieldError.checkNotNull(
              isImage, r'Attachment', 'isImage'),
          processingStatus: BuiltValueNullFieldError.checkNotNull(
              processingStatus, r'Attachment', 'processingStatus'),
          failureReason: failureReason,
          tokenCount: tokenCount,
          shortDescription: shortDescription,
          createdAt: BuiltValueNullFieldError.checkNotNull(
              createdAt, r'Attachment', 'createdAt'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
