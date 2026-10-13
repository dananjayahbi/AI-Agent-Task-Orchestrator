// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'audit_decision.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AuditDecision extends AuditDecision {
  @override
  final bool approve;
  @override
  final String? reason;

  factory _$AuditDecision([void Function(AuditDecisionBuilder)? updates]) =>
      (AuditDecisionBuilder()..update(updates))._build();

  _$AuditDecision._({required this.approve, this.reason}) : super._();
  @override
  AuditDecision rebuild(void Function(AuditDecisionBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AuditDecisionBuilder toBuilder() => AuditDecisionBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AuditDecision &&
        approve == other.approve &&
        reason == other.reason;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, approve.hashCode);
    _$hash = $jc(_$hash, reason.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AuditDecision')
          ..add('approve', approve)
          ..add('reason', reason))
        .toString();
  }
}

class AuditDecisionBuilder
    implements Builder<AuditDecision, AuditDecisionBuilder> {
  _$AuditDecision? _$v;

  bool? _approve;
  bool? get approve => _$this._approve;
  set approve(bool? approve) => _$this._approve = approve;

  String? _reason;
  String? get reason => _$this._reason;
  set reason(String? reason) => _$this._reason = reason;

  AuditDecisionBuilder() {
    AuditDecision._defaults(this);
  }

  AuditDecisionBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _approve = $v.approve;
      _reason = $v.reason;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AuditDecision other) {
    _$v = other as _$AuditDecision;
  }

  @override
  void update(void Function(AuditDecisionBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AuditDecision build() => _build();

  _$AuditDecision _build() {
    final _$result = _$v ??
        _$AuditDecision._(
          approve: BuiltValueNullFieldError.checkNotNull(
              approve, r'AuditDecision', 'approve'),
          reason: reason,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
