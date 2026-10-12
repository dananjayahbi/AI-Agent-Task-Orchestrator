// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'checkpoint_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$CheckpointListEnvelope extends CheckpointListEnvelope {
  @override
  final BuiltList<Checkpoint> results;
  @override
  final String? nextCursor;

  factory _$CheckpointListEnvelope(
          [void Function(CheckpointListEnvelopeBuilder)? updates]) =>
      (CheckpointListEnvelopeBuilder()..update(updates))._build();

  _$CheckpointListEnvelope._({required this.results, this.nextCursor})
      : super._();
  @override
  CheckpointListEnvelope rebuild(
          void Function(CheckpointListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  CheckpointListEnvelopeBuilder toBuilder() =>
      CheckpointListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is CheckpointListEnvelope &&
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
    return (newBuiltValueToStringHelper(r'CheckpointListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class CheckpointListEnvelopeBuilder
    implements Builder<CheckpointListEnvelope, CheckpointListEnvelopeBuilder> {
  _$CheckpointListEnvelope? _$v;

  ListBuilder<Checkpoint>? _results;
  ListBuilder<Checkpoint> get results =>
      _$this._results ??= ListBuilder<Checkpoint>();
  set results(ListBuilder<Checkpoint>? results) => _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  CheckpointListEnvelopeBuilder() {
    CheckpointListEnvelope._defaults(this);
  }

  CheckpointListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(CheckpointListEnvelope other) {
    _$v = other as _$CheckpointListEnvelope;
  }

  @override
  void update(void Function(CheckpointListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  CheckpointListEnvelope build() => _build();

  _$CheckpointListEnvelope _build() {
    _$CheckpointListEnvelope _$result;
    try {
      _$result = _$v ??
          _$CheckpointListEnvelope._(
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
            r'CheckpointListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
