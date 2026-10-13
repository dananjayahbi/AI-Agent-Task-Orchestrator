// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'audit_report.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AuditReport extends AuditReport {
  @override
  final String id;
  @override
  final String taskId;
  @override
  final String resolutionId;
  @override
  final String auditorSessionId;
  @override
  final JsonObject? evidence;
  @override
  final int confidence;
  @override
  final String auditorNotes;
  @override
  final ProposedVerdictEnum proposedVerdict;
  @override
  final PolicyDecisionEnum? policyDecision;
  @override
  final JsonObject? policyRuleResults;
  @override
  final DateTime createdAt;

  factory _$AuditReport([void Function(AuditReportBuilder)? updates]) =>
      (AuditReportBuilder()..update(updates))._build();

  _$AuditReport._(
      {required this.id,
      required this.taskId,
      required this.resolutionId,
      required this.auditorSessionId,
      this.evidence,
      required this.confidence,
      required this.auditorNotes,
      required this.proposedVerdict,
      this.policyDecision,
      this.policyRuleResults,
      required this.createdAt})
      : super._();
  @override
  AuditReport rebuild(void Function(AuditReportBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AuditReportBuilder toBuilder() => AuditReportBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AuditReport &&
        id == other.id &&
        taskId == other.taskId &&
        resolutionId == other.resolutionId &&
        auditorSessionId == other.auditorSessionId &&
        evidence == other.evidence &&
        confidence == other.confidence &&
        auditorNotes == other.auditorNotes &&
        proposedVerdict == other.proposedVerdict &&
        policyDecision == other.policyDecision &&
        policyRuleResults == other.policyRuleResults &&
        createdAt == other.createdAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, taskId.hashCode);
    _$hash = $jc(_$hash, resolutionId.hashCode);
    _$hash = $jc(_$hash, auditorSessionId.hashCode);
    _$hash = $jc(_$hash, evidence.hashCode);
    _$hash = $jc(_$hash, confidence.hashCode);
    _$hash = $jc(_$hash, auditorNotes.hashCode);
    _$hash = $jc(_$hash, proposedVerdict.hashCode);
    _$hash = $jc(_$hash, policyDecision.hashCode);
    _$hash = $jc(_$hash, policyRuleResults.hashCode);
    _$hash = $jc(_$hash, createdAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AuditReport')
          ..add('id', id)
          ..add('taskId', taskId)
          ..add('resolutionId', resolutionId)
          ..add('auditorSessionId', auditorSessionId)
          ..add('evidence', evidence)
          ..add('confidence', confidence)
          ..add('auditorNotes', auditorNotes)
          ..add('proposedVerdict', proposedVerdict)
          ..add('policyDecision', policyDecision)
          ..add('policyRuleResults', policyRuleResults)
          ..add('createdAt', createdAt))
        .toString();
  }
}

class AuditReportBuilder implements Builder<AuditReport, AuditReportBuilder> {
  _$AuditReport? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _taskId;
  String? get taskId => _$this._taskId;
  set taskId(String? taskId) => _$this._taskId = taskId;

  String? _resolutionId;
  String? get resolutionId => _$this._resolutionId;
  set resolutionId(String? resolutionId) => _$this._resolutionId = resolutionId;

  String? _auditorSessionId;
  String? get auditorSessionId => _$this._auditorSessionId;
  set auditorSessionId(String? auditorSessionId) =>
      _$this._auditorSessionId = auditorSessionId;

  JsonObject? _evidence;
  JsonObject? get evidence => _$this._evidence;
  set evidence(JsonObject? evidence) => _$this._evidence = evidence;

  int? _confidence;
  int? get confidence => _$this._confidence;
  set confidence(int? confidence) => _$this._confidence = confidence;

  String? _auditorNotes;
  String? get auditorNotes => _$this._auditorNotes;
  set auditorNotes(String? auditorNotes) => _$this._auditorNotes = auditorNotes;

  ProposedVerdictEnum? _proposedVerdict;
  ProposedVerdictEnum? get proposedVerdict => _$this._proposedVerdict;
  set proposedVerdict(ProposedVerdictEnum? proposedVerdict) =>
      _$this._proposedVerdict = proposedVerdict;

  PolicyDecisionEnum? _policyDecision;
  PolicyDecisionEnum? get policyDecision => _$this._policyDecision;
  set policyDecision(PolicyDecisionEnum? policyDecision) =>
      _$this._policyDecision = policyDecision;

  JsonObject? _policyRuleResults;
  JsonObject? get policyRuleResults => _$this._policyRuleResults;
  set policyRuleResults(JsonObject? policyRuleResults) =>
      _$this._policyRuleResults = policyRuleResults;

  DateTime? _createdAt;
  DateTime? get createdAt => _$this._createdAt;
  set createdAt(DateTime? createdAt) => _$this._createdAt = createdAt;

  AuditReportBuilder() {
    AuditReport._defaults(this);
  }

  AuditReportBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _taskId = $v.taskId;
      _resolutionId = $v.resolutionId;
      _auditorSessionId = $v.auditorSessionId;
      _evidence = $v.evidence;
      _confidence = $v.confidence;
      _auditorNotes = $v.auditorNotes;
      _proposedVerdict = $v.proposedVerdict;
      _policyDecision = $v.policyDecision;
      _policyRuleResults = $v.policyRuleResults;
      _createdAt = $v.createdAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AuditReport other) {
    _$v = other as _$AuditReport;
  }

  @override
  void update(void Function(AuditReportBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AuditReport build() => _build();

  _$AuditReport _build() {
    final _$result = _$v ??
        _$AuditReport._(
          id: BuiltValueNullFieldError.checkNotNull(id, r'AuditReport', 'id'),
          taskId: BuiltValueNullFieldError.checkNotNull(
              taskId, r'AuditReport', 'taskId'),
          resolutionId: BuiltValueNullFieldError.checkNotNull(
              resolutionId, r'AuditReport', 'resolutionId'),
          auditorSessionId: BuiltValueNullFieldError.checkNotNull(
              auditorSessionId, r'AuditReport', 'auditorSessionId'),
          evidence: evidence,
          confidence: BuiltValueNullFieldError.checkNotNull(
              confidence, r'AuditReport', 'confidence'),
          auditorNotes: BuiltValueNullFieldError.checkNotNull(
              auditorNotes, r'AuditReport', 'auditorNotes'),
          proposedVerdict: BuiltValueNullFieldError.checkNotNull(
              proposedVerdict, r'AuditReport', 'proposedVerdict'),
          policyDecision: policyDecision,
          policyRuleResults: policyRuleResults,
          createdAt: BuiltValueNullFieldError.checkNotNull(
              createdAt, r'AuditReport', 'createdAt'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
