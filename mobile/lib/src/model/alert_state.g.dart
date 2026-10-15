// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'alert_state.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AlertState extends AlertState {
  @override
  final String id;
  @override
  final String name;
  @override
  final String severity;
  @override
  final bool firing;
  @override
  final String status;
  @override
  final String? since;
  @override
  final BuiltMap<String, JsonObject?> signal;
  @override
  final BuiltMap<String, JsonObject?> threshold;
  @override
  final String? runbook;

  factory _$AlertState([void Function(AlertStateBuilder)? updates]) =>
      (AlertStateBuilder()..update(updates))._build();

  _$AlertState._(
      {required this.id,
      required this.name,
      required this.severity,
      required this.firing,
      required this.status,
      this.since,
      required this.signal,
      required this.threshold,
      this.runbook})
      : super._();
  @override
  AlertState rebuild(void Function(AlertStateBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AlertStateBuilder toBuilder() => AlertStateBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AlertState &&
        id == other.id &&
        name == other.name &&
        severity == other.severity &&
        firing == other.firing &&
        status == other.status &&
        since == other.since &&
        signal == other.signal &&
        threshold == other.threshold &&
        runbook == other.runbook;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, name.hashCode);
    _$hash = $jc(_$hash, severity.hashCode);
    _$hash = $jc(_$hash, firing.hashCode);
    _$hash = $jc(_$hash, status.hashCode);
    _$hash = $jc(_$hash, since.hashCode);
    _$hash = $jc(_$hash, signal.hashCode);
    _$hash = $jc(_$hash, threshold.hashCode);
    _$hash = $jc(_$hash, runbook.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AlertState')
          ..add('id', id)
          ..add('name', name)
          ..add('severity', severity)
          ..add('firing', firing)
          ..add('status', status)
          ..add('since', since)
          ..add('signal', signal)
          ..add('threshold', threshold)
          ..add('runbook', runbook))
        .toString();
  }
}

class AlertStateBuilder implements Builder<AlertState, AlertStateBuilder> {
  _$AlertState? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _name;
  String? get name => _$this._name;
  set name(String? name) => _$this._name = name;

  String? _severity;
  String? get severity => _$this._severity;
  set severity(String? severity) => _$this._severity = severity;

  bool? _firing;
  bool? get firing => _$this._firing;
  set firing(bool? firing) => _$this._firing = firing;

  String? _status;
  String? get status => _$this._status;
  set status(String? status) => _$this._status = status;

  String? _since;
  String? get since => _$this._since;
  set since(String? since) => _$this._since = since;

  MapBuilder<String, JsonObject?>? _signal;
  MapBuilder<String, JsonObject?> get signal =>
      _$this._signal ??= MapBuilder<String, JsonObject?>();
  set signal(MapBuilder<String, JsonObject?>? signal) =>
      _$this._signal = signal;

  MapBuilder<String, JsonObject?>? _threshold;
  MapBuilder<String, JsonObject?> get threshold =>
      _$this._threshold ??= MapBuilder<String, JsonObject?>();
  set threshold(MapBuilder<String, JsonObject?>? threshold) =>
      _$this._threshold = threshold;

  String? _runbook;
  String? get runbook => _$this._runbook;
  set runbook(String? runbook) => _$this._runbook = runbook;

  AlertStateBuilder() {
    AlertState._defaults(this);
  }

  AlertStateBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _name = $v.name;
      _severity = $v.severity;
      _firing = $v.firing;
      _status = $v.status;
      _since = $v.since;
      _signal = $v.signal.toBuilder();
      _threshold = $v.threshold.toBuilder();
      _runbook = $v.runbook;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AlertState other) {
    _$v = other as _$AlertState;
  }

  @override
  void update(void Function(AlertStateBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AlertState build() => _build();

  _$AlertState _build() {
    _$AlertState _$result;
    try {
      _$result = _$v ??
          _$AlertState._(
            id: BuiltValueNullFieldError.checkNotNull(id, r'AlertState', 'id'),
            name: BuiltValueNullFieldError.checkNotNull(
                name, r'AlertState', 'name'),
            severity: BuiltValueNullFieldError.checkNotNull(
                severity, r'AlertState', 'severity'),
            firing: BuiltValueNullFieldError.checkNotNull(
                firing, r'AlertState', 'firing'),
            status: BuiltValueNullFieldError.checkNotNull(
                status, r'AlertState', 'status'),
            since: since,
            signal: signal.build(),
            threshold: threshold.build(),
            runbook: runbook,
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'signal';
        signal.build();
        _$failedField = 'threshold';
        threshold.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'AlertState', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
