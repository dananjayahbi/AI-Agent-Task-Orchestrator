// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'review_decision_record.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ReviewDecisionRecord extends ReviewDecisionRecord {
  @override
  final String id;
  @override
  final String taskId;
  @override
  final String? resolutionId;
  @override
  final DecisionEnum decision;
  @override
  final String note;
  @override
  final String decidedBy;
  @override
  final DecidedViaEnum decidedVia;
  @override
  final DateTime decidedAt;

  factory _$ReviewDecisionRecord(
          [void Function(ReviewDecisionRecordBuilder)? updates]) =>
      (ReviewDecisionRecordBuilder()..update(updates))._build();

  _$ReviewDecisionRecord._(
      {required this.id,
      required this.taskId,
      this.resolutionId,
      required this.decision,
      required this.note,
      required this.decidedBy,
      required this.decidedVia,
      required this.decidedAt})
      : super._();
  @override
  ReviewDecisionRecord rebuild(
          void Function(ReviewDecisionRecordBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ReviewDecisionRecordBuilder toBuilder() =>
      ReviewDecisionRecordBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ReviewDecisionRecord &&
        id == other.id &&
        taskId == other.taskId &&
        resolutionId == other.resolutionId &&
        decision == other.decision &&
        note == other.note &&
        decidedBy == other.decidedBy &&
        decidedVia == other.decidedVia &&
        decidedAt == other.decidedAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, taskId.hashCode);
    _$hash = $jc(_$hash, resolutionId.hashCode);
    _$hash = $jc(_$hash, decision.hashCode);
    _$hash = $jc(_$hash, note.hashCode);
    _$hash = $jc(_$hash, decidedBy.hashCode);
    _$hash = $jc(_$hash, decidedVia.hashCode);
    _$hash = $jc(_$hash, decidedAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ReviewDecisionRecord')
          ..add('id', id)
          ..add('taskId', taskId)
          ..add('resolutionId', resolutionId)
          ..add('decision', decision)
          ..add('note', note)
          ..add('decidedBy', decidedBy)
          ..add('decidedVia', decidedVia)
          ..add('decidedAt', decidedAt))
        .toString();
  }
}

class ReviewDecisionRecordBuilder
    implements Builder<ReviewDecisionRecord, ReviewDecisionRecordBuilder> {
  _$ReviewDecisionRecord? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _taskId;
  String? get taskId => _$this._taskId;
  set taskId(String? taskId) => _$this._taskId = taskId;

  String? _resolutionId;
  String? get resolutionId => _$this._resolutionId;
  set resolutionId(String? resolutionId) => _$this._resolutionId = resolutionId;

  DecisionEnum? _decision;
  DecisionEnum? get decision => _$this._decision;
  set decision(DecisionEnum? decision) => _$this._decision = decision;

  String? _note;
  String? get note => _$this._note;
  set note(String? note) => _$this._note = note;

  String? _decidedBy;
  String? get decidedBy => _$this._decidedBy;
  set decidedBy(String? decidedBy) => _$this._decidedBy = decidedBy;

  DecidedViaEnum? _decidedVia;
  DecidedViaEnum? get decidedVia => _$this._decidedVia;
  set decidedVia(DecidedViaEnum? decidedVia) => _$this._decidedVia = decidedVia;

  DateTime? _decidedAt;
  DateTime? get decidedAt => _$this._decidedAt;
  set decidedAt(DateTime? decidedAt) => _$this._decidedAt = decidedAt;

  ReviewDecisionRecordBuilder() {
    ReviewDecisionRecord._defaults(this);
  }

  ReviewDecisionRecordBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _taskId = $v.taskId;
      _resolutionId = $v.resolutionId;
      _decision = $v.decision;
      _note = $v.note;
      _decidedBy = $v.decidedBy;
      _decidedVia = $v.decidedVia;
      _decidedAt = $v.decidedAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ReviewDecisionRecord other) {
    _$v = other as _$ReviewDecisionRecord;
  }

  @override
  void update(void Function(ReviewDecisionRecordBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ReviewDecisionRecord build() => _build();

  _$ReviewDecisionRecord _build() {
    final _$result = _$v ??
        _$ReviewDecisionRecord._(
          id: BuiltValueNullFieldError.checkNotNull(
              id, r'ReviewDecisionRecord', 'id'),
          taskId: BuiltValueNullFieldError.checkNotNull(
              taskId, r'ReviewDecisionRecord', 'taskId'),
          resolutionId: resolutionId,
          decision: BuiltValueNullFieldError.checkNotNull(
              decision, r'ReviewDecisionRecord', 'decision'),
          note: BuiltValueNullFieldError.checkNotNull(
              note, r'ReviewDecisionRecord', 'note'),
          decidedBy: BuiltValueNullFieldError.checkNotNull(
              decidedBy, r'ReviewDecisionRecord', 'decidedBy'),
          decidedVia: BuiltValueNullFieldError.checkNotNull(
              decidedVia, r'ReviewDecisionRecord', 'decidedVia'),
          decidedAt: BuiltValueNullFieldError.checkNotNull(
              decidedAt, r'ReviewDecisionRecord', 'decidedAt'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
