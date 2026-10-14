// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'review_decision_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ReviewDecisionResponse extends ReviewDecisionResponse {
  @override
  final ReviewDecisionRecord decision;
  @override
  final VerdictTaskState task;

  factory _$ReviewDecisionResponse(
          [void Function(ReviewDecisionResponseBuilder)? updates]) =>
      (ReviewDecisionResponseBuilder()..update(updates))._build();

  _$ReviewDecisionResponse._({required this.decision, required this.task})
      : super._();
  @override
  ReviewDecisionResponse rebuild(
          void Function(ReviewDecisionResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ReviewDecisionResponseBuilder toBuilder() =>
      ReviewDecisionResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ReviewDecisionResponse &&
        decision == other.decision &&
        task == other.task;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, decision.hashCode);
    _$hash = $jc(_$hash, task.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ReviewDecisionResponse')
          ..add('decision', decision)
          ..add('task', task))
        .toString();
  }
}

class ReviewDecisionResponseBuilder
    implements Builder<ReviewDecisionResponse, ReviewDecisionResponseBuilder> {
  _$ReviewDecisionResponse? _$v;

  ReviewDecisionRecordBuilder? _decision;
  ReviewDecisionRecordBuilder get decision =>
      _$this._decision ??= ReviewDecisionRecordBuilder();
  set decision(ReviewDecisionRecordBuilder? decision) =>
      _$this._decision = decision;

  VerdictTaskStateBuilder? _task;
  VerdictTaskStateBuilder get task =>
      _$this._task ??= VerdictTaskStateBuilder();
  set task(VerdictTaskStateBuilder? task) => _$this._task = task;

  ReviewDecisionResponseBuilder() {
    ReviewDecisionResponse._defaults(this);
  }

  ReviewDecisionResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _decision = $v.decision.toBuilder();
      _task = $v.task.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ReviewDecisionResponse other) {
    _$v = other as _$ReviewDecisionResponse;
  }

  @override
  void update(void Function(ReviewDecisionResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ReviewDecisionResponse build() => _build();

  _$ReviewDecisionResponse _build() {
    _$ReviewDecisionResponse _$result;
    try {
      _$result = _$v ??
          _$ReviewDecisionResponse._(
            decision: decision.build(),
            task: task.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'decision';
        decision.build();
        _$failedField = 'task';
        task.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'ReviewDecisionResponse', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
