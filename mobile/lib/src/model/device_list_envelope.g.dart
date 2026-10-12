// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$DeviceListEnvelope extends DeviceListEnvelope {
  @override
  final BuiltList<DeviceSummary> results;
  @override
  final String? nextCursor;

  factory _$DeviceListEnvelope(
          [void Function(DeviceListEnvelopeBuilder)? updates]) =>
      (DeviceListEnvelopeBuilder()..update(updates))._build();

  _$DeviceListEnvelope._({required this.results, this.nextCursor}) : super._();
  @override
  DeviceListEnvelope rebuild(
          void Function(DeviceListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  DeviceListEnvelopeBuilder toBuilder() =>
      DeviceListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is DeviceListEnvelope &&
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
    return (newBuiltValueToStringHelper(r'DeviceListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class DeviceListEnvelopeBuilder
    implements Builder<DeviceListEnvelope, DeviceListEnvelopeBuilder> {
  _$DeviceListEnvelope? _$v;

  ListBuilder<DeviceSummary>? _results;
  ListBuilder<DeviceSummary> get results =>
      _$this._results ??= ListBuilder<DeviceSummary>();
  set results(ListBuilder<DeviceSummary>? results) => _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  DeviceListEnvelopeBuilder() {
    DeviceListEnvelope._defaults(this);
  }

  DeviceListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(DeviceListEnvelope other) {
    _$v = other as _$DeviceListEnvelope;
  }

  @override
  void update(void Function(DeviceListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  DeviceListEnvelope build() => _build();

  _$DeviceListEnvelope _build() {
    _$DeviceListEnvelope _$result;
    try {
      _$result = _$v ??
          _$DeviceListEnvelope._(
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
            r'DeviceListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
