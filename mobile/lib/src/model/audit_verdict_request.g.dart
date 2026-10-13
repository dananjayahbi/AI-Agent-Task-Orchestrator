// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'audit_verdict_request.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AuditVerdictRequest extends AuditVerdictRequest {
  @override
  final String sessionId;
  @override
  final int leaseGeneration;
  @override
  final String taskId;
  @override
  final VerdictEnum verdict;
  @override
  final int confidence;
  @override
  final String? notes;
  @override
  final JsonObject? evidence;
  @override
  final BuiltList<BuiltMap<String, JsonObject?>>? acceptanceCriteriaResults;

  factory _$AuditVerdictRequest(
          [void Function(AuditVerdictRequestBuilder)? updates]) =>
      (AuditVerdictRequestBuilder()..update(updates))._build();

  _$AuditVerdictRequest._(
      {required this.sessionId,
      required this.leaseGeneration,
      required this.taskId,
      required this.verdict,
      required this.confidence,
      this.notes,
      this.evidence,
      this.acceptanceCriteriaResults})
      : super._();
  @override
  AuditVerdictRequest rebuild(
          void Function(AuditVerdictRequestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AuditVerdictRequestBuilder toBuilder() =>
      AuditVerdictRequestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AuditVerdictRequest &&
        sessionId == other.sessionId &&
        leaseGeneration == other.leaseGeneration &&
        taskId == other.taskId &&
        verdict == other.verdict &&
        confidence == other.confidence &&
        notes == other.notes &&
        evidence == other.evidence &&
        acceptanceCriteriaResults == other.acceptanceCriteriaResults;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, sessionId.hashCode);
    _$hash = $jc(_$hash, leaseGeneration.hashCode);
    _$hash = $jc(_$hash, taskId.hashCode);
    _$hash = $jc(_$hash, verdict.hashCode);
    _$hash = $jc(_$hash, confidence.hashCode);
    _$hash = $jc(_$hash, notes.hashCode);
    _$hash = $jc(_$hash, evidence.hashCode);
    _$hash = $jc(_$hash, acceptanceCriteriaResults.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AuditVerdictRequest')
          ..add('sessionId', sessionId)
          ..add('leaseGeneration', leaseGeneration)
          ..add('taskId', taskId)
          ..add('verdict', verdict)
          ..add('confidence', confidence)
          ..add('notes', notes)
          ..add('evidence', evidence)
          ..add('acceptanceCriteriaResults', acceptanceCriteriaResults))
        .toString();
  }
}

class AuditVerdictRequestBuilder
    implements Builder<AuditVerdictRequest, AuditVerdictRequestBuilder> {
  _$AuditVerdictRequest? _$v;

  String? _sessionId;
  String? get sessionId => _$this._sessionId;
  set sessionId(String? sessionId) => _$this._sessionId = sessionId;

  int? _leaseGeneration;
  int? get leaseGeneration => _$this._leaseGeneration;
  set leaseGeneration(int? leaseGeneration) =>
      _$this._leaseGeneration = leaseGeneration;

  String? _taskId;
  String? get taskId => _$this._taskId;
  set taskId(String? taskId) => _$this._taskId = taskId;

  VerdictEnum? _verdict;
  VerdictEnum? get verdict => _$this._verdict;
  set verdict(VerdictEnum? verdict) => _$this._verdict = verdict;

  int? _confidence;
  int? get confidence => _$this._confidence;
  set confidence(int? confidence) => _$this._confidence = confidence;

  String? _notes;
  String? get notes => _$this._notes;
  set notes(String? notes) => _$this._notes = notes;

  JsonObject? _evidence;
  JsonObject? get evidence => _$this._evidence;
  set evidence(JsonObject? evidence) => _$this._evidence = evidence;

  ListBuilder<BuiltMap<String, JsonObject?>>? _acceptanceCriteriaResults;
  ListBuilder<BuiltMap<String, JsonObject?>> get acceptanceCriteriaResults =>
      _$this._acceptanceCriteriaResults ??=
          ListBuilder<BuiltMap<String, JsonObject?>>();
  set acceptanceCriteriaResults(
          ListBuilder<BuiltMap<String, JsonObject?>>?
              acceptanceCriteriaResults) =>
      _$this._acceptanceCriteriaResults = acceptanceCriteriaResults;

  AuditVerdictRequestBuilder() {
    AuditVerdictRequest._defaults(this);
  }

  AuditVerdictRequestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _sessionId = $v.sessionId;
      _leaseGeneration = $v.leaseGeneration;
      _taskId = $v.taskId;
      _verdict = $v.verdict;
      _confidence = $v.confidence;
      _notes = $v.notes;
      _evidence = $v.evidence;
      _acceptanceCriteriaResults = $v.acceptanceCriteriaResults?.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AuditVerdictRequest other) {
    _$v = other as _$AuditVerdictRequest;
  }

  @override
  void update(void Function(AuditVerdictRequestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AuditVerdictRequest build() => _build();

  _$AuditVerdictRequest _build() {
    _$AuditVerdictRequest _$result;
    try {
      _$result = _$v ??
          _$AuditVerdictRequest._(
            sessionId: BuiltValueNullFieldError.checkNotNull(
                sessionId, r'AuditVerdictRequest', 'sessionId'),
            leaseGeneration: BuiltValueNullFieldError.checkNotNull(
                leaseGeneration, r'AuditVerdictRequest', 'leaseGeneration'),
            taskId: BuiltValueNullFieldError.checkNotNull(
                taskId, r'AuditVerdictRequest', 'taskId'),
            verdict: BuiltValueNullFieldError.checkNotNull(
                verdict, r'AuditVerdictRequest', 'verdict'),
            confidence: BuiltValueNullFieldError.checkNotNull(
                confidence, r'AuditVerdictRequest', 'confidence'),
            notes: notes,
            evidence: evidence,
            acceptanceCriteriaResults: _acceptanceCriteriaResults?.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'acceptanceCriteriaResults';
        _acceptanceCriteriaResults?.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'AuditVerdictRequest', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
