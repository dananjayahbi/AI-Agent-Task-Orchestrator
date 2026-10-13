// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'resolution_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ResolutionListEnvelope extends ResolutionListEnvelope {
  @override
  final BuiltList<Resolution> results;
  @override
  final String? nextCursor;

  factory _$ResolutionListEnvelope(
          [void Function(ResolutionListEnvelopeBuilder)? updates]) =>
      (ResolutionListEnvelopeBuilder()..update(updates))._build();

  _$ResolutionListEnvelope._({required this.results, this.nextCursor})
      : super._();
  @override
  ResolutionListEnvelope rebuild(
          void Function(ResolutionListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ResolutionListEnvelopeBuilder toBuilder() =>
      ResolutionListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ResolutionListEnvelope &&
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
    return (newBuiltValueToStringHelper(r'ResolutionListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class ResolutionListEnvelopeBuilder
    implements Builder<ResolutionListEnvelope, ResolutionListEnvelopeBuilder> {
  _$ResolutionListEnvelope? _$v;

  ListBuilder<Resolution>? _results;
  ListBuilder<Resolution> get results =>
      _$this._results ??= ListBuilder<Resolution>();
  set results(ListBuilder<Resolution>? results) => _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  ResolutionListEnvelopeBuilder() {
    ResolutionListEnvelope._defaults(this);
  }

  ResolutionListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ResolutionListEnvelope other) {
    _$v = other as _$ResolutionListEnvelope;
  }

  @override
  void update(void Function(ResolutionListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ResolutionListEnvelope build() => _build();

  _$ResolutionListEnvelope _build() {
    _$ResolutionListEnvelope _$result;
    try {
      _$result = _$v ??
          _$ResolutionListEnvelope._(
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
            r'ResolutionListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
