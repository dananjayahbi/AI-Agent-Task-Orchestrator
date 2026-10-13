// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'attachment_delete.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AttachmentDelete extends AttachmentDelete {
  @override
  final String id;
  @override
  final String taskId;
  @override
  final DateTime deletedAt;

  factory _$AttachmentDelete(
          [void Function(AttachmentDeleteBuilder)? updates]) =>
      (AttachmentDeleteBuilder()..update(updates))._build();

  _$AttachmentDelete._(
      {required this.id, required this.taskId, required this.deletedAt})
      : super._();
  @override
  AttachmentDelete rebuild(void Function(AttachmentDeleteBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AttachmentDeleteBuilder toBuilder() =>
      AttachmentDeleteBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AttachmentDelete &&
        id == other.id &&
        taskId == other.taskId &&
        deletedAt == other.deletedAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, taskId.hashCode);
    _$hash = $jc(_$hash, deletedAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AttachmentDelete')
          ..add('id', id)
          ..add('taskId', taskId)
          ..add('deletedAt', deletedAt))
        .toString();
  }
}

class AttachmentDeleteBuilder
    implements Builder<AttachmentDelete, AttachmentDeleteBuilder> {
  _$AttachmentDelete? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _taskId;
  String? get taskId => _$this._taskId;
  set taskId(String? taskId) => _$this._taskId = taskId;

  DateTime? _deletedAt;
  DateTime? get deletedAt => _$this._deletedAt;
  set deletedAt(DateTime? deletedAt) => _$this._deletedAt = deletedAt;

  AttachmentDeleteBuilder() {
    AttachmentDelete._defaults(this);
  }

  AttachmentDeleteBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _taskId = $v.taskId;
      _deletedAt = $v.deletedAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AttachmentDelete other) {
    _$v = other as _$AttachmentDelete;
  }

  @override
  void update(void Function(AttachmentDeleteBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AttachmentDelete build() => _build();

  _$AttachmentDelete _build() {
    final _$result = _$v ??
        _$AttachmentDelete._(
          id: BuiltValueNullFieldError.checkNotNull(
              id, r'AttachmentDelete', 'id'),
          taskId: BuiltValueNullFieldError.checkNotNull(
              taskId, r'AttachmentDelete', 'taskId'),
          deletedAt: BuiltValueNullFieldError.checkNotNull(
              deletedAt, r'AttachmentDelete', 'deletedAt'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
