// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'token_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$TokenListEnvelope extends TokenListEnvelope {
  @override
  final BuiltList<TokenSummary> results;
  @override
  final String? nextCursor;

  factory _$TokenListEnvelope(
          [void Function(TokenListEnvelopeBuilder)? updates]) =>
      (TokenListEnvelopeBuilder()..update(updates))._build();

  _$TokenListEnvelope._({required this.results, this.nextCursor}) : super._();
  @override
  TokenListEnvelope rebuild(void Function(TokenListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  TokenListEnvelopeBuilder toBuilder() =>
      TokenListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is TokenListEnvelope &&
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
    return (newBuiltValueToStringHelper(r'TokenListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class TokenListEnvelopeBuilder
    implements Builder<TokenListEnvelope, TokenListEnvelopeBuilder> {
  _$TokenListEnvelope? _$v;

  ListBuilder<TokenSummary>? _results;
  ListBuilder<TokenSummary> get results =>
      _$this._results ??= ListBuilder<TokenSummary>();
  set results(ListBuilder<TokenSummary>? results) => _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  TokenListEnvelopeBuilder() {
    TokenListEnvelope._defaults(this);
  }

  TokenListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(TokenListEnvelope other) {
    _$v = other as _$TokenListEnvelope;
  }

  @override
  void update(void Function(TokenListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  TokenListEnvelope build() => _build();

  _$TokenListEnvelope _build() {
    _$TokenListEnvelope _$result;
    try {
      _$result = _$v ??
          _$TokenListEnvelope._(
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
            r'TokenListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
