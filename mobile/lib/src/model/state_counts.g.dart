// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'state_counts.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$StateCounts extends StateCounts {
  @override
  final int draft;
  @override
  final int pending;
  @override
  final int inProgress;
  @override
  final int toBeAudited;
  @override
  final int inHumanReview;
  @override
  final int completed;

  factory _$StateCounts([void Function(StateCountsBuilder)? updates]) =>
      (StateCountsBuilder()..update(updates))._build();

  _$StateCounts._(
      {required this.draft,
      required this.pending,
      required this.inProgress,
      required this.toBeAudited,
      required this.inHumanReview,
      required this.completed})
      : super._();
  @override
  StateCounts rebuild(void Function(StateCountsBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  StateCountsBuilder toBuilder() => StateCountsBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is StateCounts &&
        draft == other.draft &&
        pending == other.pending &&
        inProgress == other.inProgress &&
        toBeAudited == other.toBeAudited &&
        inHumanReview == other.inHumanReview &&
        completed == other.completed;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, draft.hashCode);
    _$hash = $jc(_$hash, pending.hashCode);
    _$hash = $jc(_$hash, inProgress.hashCode);
    _$hash = $jc(_$hash, toBeAudited.hashCode);
    _$hash = $jc(_$hash, inHumanReview.hashCode);
    _$hash = $jc(_$hash, completed.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'StateCounts')
          ..add('draft', draft)
          ..add('pending', pending)
          ..add('inProgress', inProgress)
          ..add('toBeAudited', toBeAudited)
          ..add('inHumanReview', inHumanReview)
          ..add('completed', completed))
        .toString();
  }
}

class StateCountsBuilder implements Builder<StateCounts, StateCountsBuilder> {
  _$StateCounts? _$v;

  int? _draft;
  int? get draft => _$this._draft;
  set draft(int? draft) => _$this._draft = draft;

  int? _pending;
  int? get pending => _$this._pending;
  set pending(int? pending) => _$this._pending = pending;

  int? _inProgress;
  int? get inProgress => _$this._inProgress;
  set inProgress(int? inProgress) => _$this._inProgress = inProgress;

  int? _toBeAudited;
  int? get toBeAudited => _$this._toBeAudited;
  set toBeAudited(int? toBeAudited) => _$this._toBeAudited = toBeAudited;

  int? _inHumanReview;
  int? get inHumanReview => _$this._inHumanReview;
  set inHumanReview(int? inHumanReview) =>
      _$this._inHumanReview = inHumanReview;

  int? _completed;
  int? get completed => _$this._completed;
  set completed(int? completed) => _$this._completed = completed;

  StateCountsBuilder() {
    StateCounts._defaults(this);
  }

  StateCountsBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _draft = $v.draft;
      _pending = $v.pending;
      _inProgress = $v.inProgress;
      _toBeAudited = $v.toBeAudited;
      _inHumanReview = $v.inHumanReview;
      _completed = $v.completed;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(StateCounts other) {
    _$v = other as _$StateCounts;
  }

  @override
  void update(void Function(StateCountsBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  StateCounts build() => _build();

  _$StateCounts _build() {
    final _$result = _$v ??
        _$StateCounts._(
          draft: BuiltValueNullFieldError.checkNotNull(
              draft, r'StateCounts', 'draft'),
          pending: BuiltValueNullFieldError.checkNotNull(
              pending, r'StateCounts', 'pending'),
          inProgress: BuiltValueNullFieldError.checkNotNull(
              inProgress, r'StateCounts', 'inProgress'),
          toBeAudited: BuiltValueNullFieldError.checkNotNull(
              toBeAudited, r'StateCounts', 'toBeAudited'),
          inHumanReview: BuiltValueNullFieldError.checkNotNull(
              inHumanReview, r'StateCounts', 'inHumanReview'),
          completed: BuiltValueNullFieldError.checkNotNull(
              completed, r'StateCounts', 'completed'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
