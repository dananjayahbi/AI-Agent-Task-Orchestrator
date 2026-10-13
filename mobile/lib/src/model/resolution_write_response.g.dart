// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'resolution_write_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ResolutionWriteResponse extends ResolutionWriteResponse {
  @override
  final Resolution resolution;
  @override
  final ResolutionTaskState task;
  @override
  final String trigger;
  @override
  final BuiltList<String> scopeViolations;

  factory _$ResolutionWriteResponse(
          [void Function(ResolutionWriteResponseBuilder)? updates]) =>
      (ResolutionWriteResponseBuilder()..update(updates))._build();

  _$ResolutionWriteResponse._(
      {required this.resolution,
      required this.task,
      required this.trigger,
      required this.scopeViolations})
      : super._();
  @override
  ResolutionWriteResponse rebuild(
          void Function(ResolutionWriteResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ResolutionWriteResponseBuilder toBuilder() =>
      ResolutionWriteResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ResolutionWriteResponse &&
        resolution == other.resolution &&
        task == other.task &&
        trigger == other.trigger &&
        scopeViolations == other.scopeViolations;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, resolution.hashCode);
    _$hash = $jc(_$hash, task.hashCode);
    _$hash = $jc(_$hash, trigger.hashCode);
    _$hash = $jc(_$hash, scopeViolations.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ResolutionWriteResponse')
          ..add('resolution', resolution)
          ..add('task', task)
          ..add('trigger', trigger)
          ..add('scopeViolations', scopeViolations))
        .toString();
  }
}

class ResolutionWriteResponseBuilder
    implements
        Builder<ResolutionWriteResponse, ResolutionWriteResponseBuilder> {
  _$ResolutionWriteResponse? _$v;

  ResolutionBuilder? _resolution;
  ResolutionBuilder get resolution =>
      _$this._resolution ??= ResolutionBuilder();
  set resolution(ResolutionBuilder? resolution) =>
      _$this._resolution = resolution;

  ResolutionTaskStateBuilder? _task;
  ResolutionTaskStateBuilder get task =>
      _$this._task ??= ResolutionTaskStateBuilder();
  set task(ResolutionTaskStateBuilder? task) => _$this._task = task;

  String? _trigger;
  String? get trigger => _$this._trigger;
  set trigger(String? trigger) => _$this._trigger = trigger;

  ListBuilder<String>? _scopeViolations;
  ListBuilder<String> get scopeViolations =>
      _$this._scopeViolations ??= ListBuilder<String>();
  set scopeViolations(ListBuilder<String>? scopeViolations) =>
      _$this._scopeViolations = scopeViolations;

  ResolutionWriteResponseBuilder() {
    ResolutionWriteResponse._defaults(this);
  }

  ResolutionWriteResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _resolution = $v.resolution.toBuilder();
      _task = $v.task.toBuilder();
      _trigger = $v.trigger;
      _scopeViolations = $v.scopeViolations.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ResolutionWriteResponse other) {
    _$v = other as _$ResolutionWriteResponse;
  }

  @override
  void update(void Function(ResolutionWriteResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ResolutionWriteResponse build() => _build();

  _$ResolutionWriteResponse _build() {
    _$ResolutionWriteResponse _$result;
    try {
      _$result = _$v ??
          _$ResolutionWriteResponse._(
            resolution: resolution.build(),
            task: task.build(),
            trigger: BuiltValueNullFieldError.checkNotNull(
                trigger, r'ResolutionWriteResponse', 'trigger'),
            scopeViolations: scopeViolations.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'resolution';
        resolution.build();
        _$failedField = 'task';
        task.build();

        _$failedField = 'scopeViolations';
        scopeViolations.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'ResolutionWriteResponse', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
