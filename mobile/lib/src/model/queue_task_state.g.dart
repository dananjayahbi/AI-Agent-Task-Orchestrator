// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'queue_task_state.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$QueueTaskState extends QueueTaskState {
  @override
  final String id;
  @override
  final String state;
  @override
  final int version;
  @override
  final String? reviewReason;
  @override
  final String mergeStatus;

  factory _$QueueTaskState([void Function(QueueTaskStateBuilder)? updates]) =>
      (QueueTaskStateBuilder()..update(updates))._build();

  _$QueueTaskState._(
      {required this.id,
      required this.state,
      required this.version,
      this.reviewReason,
      required this.mergeStatus})
      : super._();
  @override
  QueueTaskState rebuild(void Function(QueueTaskStateBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  QueueTaskStateBuilder toBuilder() => QueueTaskStateBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is QueueTaskState &&
        id == other.id &&
        state == other.state &&
        version == other.version &&
        reviewReason == other.reviewReason &&
        mergeStatus == other.mergeStatus;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, state.hashCode);
    _$hash = $jc(_$hash, version.hashCode);
    _$hash = $jc(_$hash, reviewReason.hashCode);
    _$hash = $jc(_$hash, mergeStatus.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'QueueTaskState')
          ..add('id', id)
          ..add('state', state)
          ..add('version', version)
          ..add('reviewReason', reviewReason)
          ..add('mergeStatus', mergeStatus))
        .toString();
  }
}

class QueueTaskStateBuilder
    implements Builder<QueueTaskState, QueueTaskStateBuilder> {
  _$QueueTaskState? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _state;
  String? get state => _$this._state;
  set state(String? state) => _$this._state = state;

  int? _version;
  int? get version => _$this._version;
  set version(int? version) => _$this._version = version;

  String? _reviewReason;
  String? get reviewReason => _$this._reviewReason;
  set reviewReason(String? reviewReason) => _$this._reviewReason = reviewReason;

  String? _mergeStatus;
  String? get mergeStatus => _$this._mergeStatus;
  set mergeStatus(String? mergeStatus) => _$this._mergeStatus = mergeStatus;

  QueueTaskStateBuilder() {
    QueueTaskState._defaults(this);
  }

  QueueTaskStateBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _state = $v.state;
      _version = $v.version;
      _reviewReason = $v.reviewReason;
      _mergeStatus = $v.mergeStatus;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(QueueTaskState other) {
    _$v = other as _$QueueTaskState;
  }

  @override
  void update(void Function(QueueTaskStateBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  QueueTaskState build() => _build();

  _$QueueTaskState _build() {
    final _$result = _$v ??
        _$QueueTaskState._(
          id: BuiltValueNullFieldError.checkNotNull(
              id, r'QueueTaskState', 'id'),
          state: BuiltValueNullFieldError.checkNotNull(
              state, r'QueueTaskState', 'state'),
          version: BuiltValueNullFieldError.checkNotNull(
              version, r'QueueTaskState', 'version'),
          reviewReason: reviewReason,
          mergeStatus: BuiltValueNullFieldError.checkNotNull(
              mergeStatus, r'QueueTaskState', 'mergeStatus'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
