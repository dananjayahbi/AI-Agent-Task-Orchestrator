// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'audit_verdict_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AuditVerdictResponse extends AuditVerdictResponse {
  @override
  final AuditReport report;
  @override
  final VerdictTaskState task;
  @override
  final String trigger;
  @override
  final AuditDecision decision;

  factory _$AuditVerdictResponse(
          [void Function(AuditVerdictResponseBuilder)? updates]) =>
      (AuditVerdictResponseBuilder()..update(updates))._build();

  _$AuditVerdictResponse._(
      {required this.report,
      required this.task,
      required this.trigger,
      required this.decision})
      : super._();
  @override
  AuditVerdictResponse rebuild(
          void Function(AuditVerdictResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AuditVerdictResponseBuilder toBuilder() =>
      AuditVerdictResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AuditVerdictResponse &&
        report == other.report &&
        task == other.task &&
        trigger == other.trigger &&
        decision == other.decision;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, report.hashCode);
    _$hash = $jc(_$hash, task.hashCode);
    _$hash = $jc(_$hash, trigger.hashCode);
    _$hash = $jc(_$hash, decision.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AuditVerdictResponse')
          ..add('report', report)
          ..add('task', task)
          ..add('trigger', trigger)
          ..add('decision', decision))
        .toString();
  }
}

class AuditVerdictResponseBuilder
    implements Builder<AuditVerdictResponse, AuditVerdictResponseBuilder> {
  _$AuditVerdictResponse? _$v;

  AuditReportBuilder? _report;
  AuditReportBuilder get report => _$this._report ??= AuditReportBuilder();
  set report(AuditReportBuilder? report) => _$this._report = report;

  VerdictTaskStateBuilder? _task;
  VerdictTaskStateBuilder get task =>
      _$this._task ??= VerdictTaskStateBuilder();
  set task(VerdictTaskStateBuilder? task) => _$this._task = task;

  String? _trigger;
  String? get trigger => _$this._trigger;
  set trigger(String? trigger) => _$this._trigger = trigger;

  AuditDecisionBuilder? _decision;
  AuditDecisionBuilder get decision =>
      _$this._decision ??= AuditDecisionBuilder();
  set decision(AuditDecisionBuilder? decision) => _$this._decision = decision;

  AuditVerdictResponseBuilder() {
    AuditVerdictResponse._defaults(this);
  }

  AuditVerdictResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _report = $v.report.toBuilder();
      _task = $v.task.toBuilder();
      _trigger = $v.trigger;
      _decision = $v.decision.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AuditVerdictResponse other) {
    _$v = other as _$AuditVerdictResponse;
  }

  @override
  void update(void Function(AuditVerdictResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AuditVerdictResponse build() => _build();

  _$AuditVerdictResponse _build() {
    _$AuditVerdictResponse _$result;
    try {
      _$result = _$v ??
          _$AuditVerdictResponse._(
            report: report.build(),
            task: task.build(),
            trigger: BuiltValueNullFieldError.checkNotNull(
                trigger, r'AuditVerdictResponse', 'trigger'),
            decision: decision.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'report';
        report.build();
        _$failedField = 'task';
        task.build();

        _$failedField = 'decision';
        decision.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'AuditVerdictResponse', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
