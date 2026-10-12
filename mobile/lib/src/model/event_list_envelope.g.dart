// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'event_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$EventListEnvelope extends EventListEnvelope {
  @override
  final BuiltList<EventEnvelope> results;
  @override
  final String? nextCursor;

  factory _$EventListEnvelope(
          [void Function(EventListEnvelopeBuilder)? updates]) =>
      (EventListEnvelopeBuilder()..update(updates))._build();

  _$EventListEnvelope._({required this.results, this.nextCursor}) : super._();
  @override
  EventListEnvelope rebuild(void Function(EventListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  EventListEnvelopeBuilder toBuilder() =>
      EventListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is EventListEnvelope &&
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
    return (newBuiltValueToStringHelper(r'EventListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class EventListEnvelopeBuilder
    implements Builder<EventListEnvelope, EventListEnvelopeBuilder> {
  _$EventListEnvelope? _$v;

  ListBuilder<EventEnvelope>? _results;
  ListBuilder<EventEnvelope> get results =>
      _$this._results ??= ListBuilder<EventEnvelope>();
  set results(ListBuilder<EventEnvelope>? results) => _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  EventListEnvelopeBuilder() {
    EventListEnvelope._defaults(this);
  }

  EventListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(EventListEnvelope other) {
    _$v = other as _$EventListEnvelope;
  }

  @override
  void update(void Function(EventListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  EventListEnvelope build() => _build();

  _$EventListEnvelope _build() {
    _$EventListEnvelope _$result;
    try {
      _$result = _$v ??
          _$EventListEnvelope._(
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
            r'EventListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
