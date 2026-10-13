// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'resolution_task_state.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ResolutionTaskState extends ResolutionTaskState {
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

  factory _$ResolutionTaskState(
          [void Function(ResolutionTaskStateBuilder)? updates]) =>
      (ResolutionTaskStateBuilder()..update(updates))._build();

  _$ResolutionTaskState._(
      {required this.id,
      required this.state,
      required this.version,
      this.reviewReason,
      required this.mergeStatus})
      : super._();
  @override
  ResolutionTaskState rebuild(
          void Function(ResolutionTaskStateBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ResolutionTaskStateBuilder toBuilder() =>
      ResolutionTaskStateBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ResolutionTaskState &&
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
    return (newBuiltValueToStringHelper(r'ResolutionTaskState')
          ..add('id', id)
          ..add('state', state)
          ..add('version', version)
          ..add('reviewReason', reviewReason)
          ..add('mergeStatus', mergeStatus))
        .toString();
  }
}

class ResolutionTaskStateBuilder
    implements Builder<ResolutionTaskState, ResolutionTaskStateBuilder> {
  _$ResolutionTaskState? _$v;

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

  ResolutionTaskStateBuilder() {
    ResolutionTaskState._defaults(this);
  }

  ResolutionTaskStateBuilder get _$this {
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
  void replace(ResolutionTaskState other) {
    _$v = other as _$ResolutionTaskState;
  }

  @override
  void update(void Function(ResolutionTaskStateBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ResolutionTaskState build() => _build();

  _$ResolutionTaskState _build() {
    final _$result = _$v ??
        _$ResolutionTaskState._(
          id: BuiltValueNullFieldError.checkNotNull(
              id, r'ResolutionTaskState', 'id'),
          state: BuiltValueNullFieldError.checkNotNull(
              state, r'ResolutionTaskState', 'state'),
          version: BuiltValueNullFieldError.checkNotNull(
              version, r'ResolutionTaskState', 'version'),
          reviewReason: reviewReason,
          mergeStatus: BuiltValueNullFieldError.checkNotNull(
              mergeStatus, r'ResolutionTaskState', 'mergeStatus'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
