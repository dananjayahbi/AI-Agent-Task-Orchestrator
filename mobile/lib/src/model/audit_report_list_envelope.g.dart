// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'audit_report_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AuditReportListEnvelope extends AuditReportListEnvelope {
  @override
  final BuiltList<AuditReport> results;
  @override
  final String? nextCursor;

  factory _$AuditReportListEnvelope(
          [void Function(AuditReportListEnvelopeBuilder)? updates]) =>
      (AuditReportListEnvelopeBuilder()..update(updates))._build();

  _$AuditReportListEnvelope._({required this.results, this.nextCursor})
      : super._();
  @override
  AuditReportListEnvelope rebuild(
          void Function(AuditReportListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AuditReportListEnvelopeBuilder toBuilder() =>
      AuditReportListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AuditReportListEnvelope &&
        results == other.results &&
        nextCursor == other.nextCursor;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, results.hashCode);
    _$hash = $jc(_$hash, nextCursor.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AuditReportListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class AuditReportListEnvelopeBuilder
    implements
        Builder<AuditReportListEnvelope, AuditReportListEnvelopeBuilder> {
  _$AuditReportListEnvelope? _$v;

  ListBuilder<AuditReport>? _results;
  ListBuilder<AuditReport> get results =>
      _$this._results ??= ListBuilder<AuditReport>();
  set results(ListBuilder<AuditReport>? results) => _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  AuditReportListEnvelopeBuilder() {
    AuditReportListEnvelope._defaults(this);
  }

  AuditReportListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AuditReportListEnvelope other) {
    _$v = other as _$AuditReportListEnvelope;
  }

  @override
  void update(void Function(AuditReportListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AuditReportListEnvelope build() => _build();

  _$AuditReportListEnvelope _build() {
    _$AuditReportListEnvelope _$result;
    try {
      _$result = _$v ??
          _$AuditReportListEnvelope._(
            results: results.build(),
            nextCursor: nextCursor,
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'results';
        results.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'AuditReportListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
