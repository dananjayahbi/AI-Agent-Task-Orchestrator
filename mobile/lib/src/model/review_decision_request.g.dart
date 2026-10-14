// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'review_decision_request.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ReviewDecisionRequest extends ReviewDecisionRequest {
  @override
  final DecisionEnum decision;
  @override
  final String? note;
  @override
  final String? resolutionId;
  @override
  final int version;

  factory _$ReviewDecisionRequest(
          [void Function(ReviewDecisionRequestBuilder)? updates]) =>
      (ReviewDecisionRequestBuilder()..update(updates))._build();

  _$ReviewDecisionRequest._(
      {required this.decision,
      this.note,
      this.resolutionId,
      required this.version})
      : super._();
  @override
  ReviewDecisionRequest rebuild(
          void Function(ReviewDecisionRequestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ReviewDecisionRequestBuilder toBuilder() =>
      ReviewDecisionRequestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ReviewDecisionRequest &&
        decision == other.decision &&
        note == other.note &&
        resolutionId == other.resolutionId &&
        version == other.version;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, decision.hashCode);
    _$hash = $jc(_$hash, note.hashCode);
    _$hash = $jc(_$hash, resolutionId.hashCode);
    _$hash = $jc(_$hash, version.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ReviewDecisionRequest')
          ..add('decision', decision)
          ..add('note', note)
          ..add('resolutionId', resolutionId)
          ..add('version', version))
        .toString();
  }
}

class ReviewDecisionRequestBuilder
    implements Builder<ReviewDecisionRequest, ReviewDecisionRequestBuilder> {
  _$ReviewDecisionRequest? _$v;

  DecisionEnum? _decision;
  DecisionEnum? get decision => _$this._decision;
  set decision(DecisionEnum? decision) => _$this._decision = decision;

  String? _note;
  String? get note => _$this._note;
  set note(String? note) => _$this._note = note;

  String? _resolutionId;
  String? get resolutionId => _$this._resolutionId;
  set resolutionId(String? resolutionId) => _$this._resolutionId = resolutionId;

  int? _version;
  int? get version => _$this._version;
  set version(int? version) => _$this._version = version;

  ReviewDecisionRequestBuilder() {
    ReviewDecisionRequest._defaults(this);
  }

  ReviewDecisionRequestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _decision = $v.decision;
      _note = $v.note;
      _resolutionId = $v.resolutionId;
      _version = $v.version;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ReviewDecisionRequest other) {
    _$v = other as _$ReviewDecisionRequest;
  }

  @override
  void update(void Function(ReviewDecisionRequestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ReviewDecisionRequest build() => _build();

  _$ReviewDecisionRequest _build() {
    final _$result = _$v ??
        _$ReviewDecisionRequest._(
          decision: BuiltValueNullFieldError.checkNotNull(
              decision, r'ReviewDecisionRequest', 'decision'),
          note: note,
          resolutionId: resolutionId,
          version: BuiltValueNullFieldError.checkNotNull(
              version, r'ReviewDecisionRequest', 'version'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
