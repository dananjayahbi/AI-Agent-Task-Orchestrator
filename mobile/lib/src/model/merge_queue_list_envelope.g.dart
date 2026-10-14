// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'merge_queue_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$MergeQueueListEnvelope extends MergeQueueListEnvelope {
  @override
  final BuiltList<MergeQueueItem> results;
  @override
  final String? nextCursor;

  factory _$MergeQueueListEnvelope(
          [void Function(MergeQueueListEnvelopeBuilder)? updates]) =>
      (MergeQueueListEnvelopeBuilder()..update(updates))._build();

  _$MergeQueueListEnvelope._({required this.results, this.nextCursor})
      : super._();
  @override
  MergeQueueListEnvelope rebuild(
          void Function(MergeQueueListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  MergeQueueListEnvelopeBuilder toBuilder() =>
      MergeQueueListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is MergeQueueListEnvelope &&
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
    return (newBuiltValueToStringHelper(r'MergeQueueListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class MergeQueueListEnvelopeBuilder
    implements Builder<MergeQueueListEnvelope, MergeQueueListEnvelopeBuilder> {
  _$MergeQueueListEnvelope? _$v;

  ListBuilder<MergeQueueItem>? _results;
  ListBuilder<MergeQueueItem> get results =>
      _$this._results ??= ListBuilder<MergeQueueItem>();
  set results(ListBuilder<MergeQueueItem>? results) =>
      _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  MergeQueueListEnvelopeBuilder() {
    MergeQueueListEnvelope._defaults(this);
  }

  MergeQueueListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(MergeQueueListEnvelope other) {
    _$v = other as _$MergeQueueListEnvelope;
  }

  @override
  void update(void Function(MergeQueueListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  MergeQueueListEnvelope build() => _build();

  _$MergeQueueListEnvelope _build() {
    _$MergeQueueListEnvelope _$result;
    try {
      _$result = _$v ??
          _$MergeQueueListEnvelope._(
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
            r'MergeQueueListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
