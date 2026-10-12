// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'checkpoint.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$Checkpoint extends Checkpoint {
  @override
  final String id;
  @override
  final String taskId;
  @override
  final int attemptNumber;
  @override
  final String sessionId;
  @override
  final DateTime timestamp;
  @override
  final String message;
  @override
  final int? percent;
  @override
  final JsonObject? tokenUsage;
  @override
  final String kind;

  factory _$Checkpoint([void Function(CheckpointBuilder)? updates]) =>
      (CheckpointBuilder()..update(updates))._build();

  _$Checkpoint._(
      {required this.id,
      required this.taskId,
      required this.attemptNumber,
      required this.sessionId,
      required this.timestamp,
      required this.message,
      this.percent,
      this.tokenUsage,
      required this.kind})
      : super._();
  @override
  Checkpoint rebuild(void Function(CheckpointBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  CheckpointBuilder toBuilder() => CheckpointBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is Checkpoint &&
        id == other.id &&
        taskId == other.taskId &&
        attemptNumber == other.attemptNumber &&
        sessionId == other.sessionId &&
        timestamp == other.timestamp &&
        message == other.message &&
        percent == other.percent &&
        tokenUsage == other.tokenUsage &&
        kind == other.kind;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, taskId.hashCode);
    _$hash = $jc(_$hash, attemptNumber.hashCode);
    _$hash = $jc(_$hash, sessionId.hashCode);
    _$hash = $jc(_$hash, timestamp.hashCode);
    _$hash = $jc(_$hash, message.hashCode);
    _$hash = $jc(_$hash, percent.hashCode);
    _$hash = $jc(_$hash, tokenUsage.hashCode);
    _$hash = $jc(_$hash, kind.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'Checkpoint')
          ..add('id', id)
          ..add('taskId', taskId)
          ..add('attemptNumber', attemptNumber)
          ..add('sessionId', sessionId)
          ..add('timestamp', timestamp)
          ..add('message', message)
          ..add('percent', percent)
          ..add('tokenUsage', tokenUsage)
          ..add('kind', kind))
        .toString();
  }
}

class CheckpointBuilder implements Builder<Checkpoint, CheckpointBuilder> {
  _$Checkpoint? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _taskId;
  String? get taskId => _$this._taskId;
  set taskId(String? taskId) => _$this._taskId = taskId;

  int? _attemptNumber;
  int? get attemptNumber => _$this._attemptNumber;
  set attemptNumber(int? attemptNumber) =>
      _$this._attemptNumber = attemptNumber;

  String? _sessionId;
  String? get sessionId => _$this._sessionId;
  set sessionId(String? sessionId) => _$this._sessionId = sessionId;

  DateTime? _timestamp;
  DateTime? get timestamp => _$this._timestamp;
  set timestamp(DateTime? timestamp) => _$this._timestamp = timestamp;

  String? _message;
  String? get message => _$this._message;
  set message(String? message) => _$this._message = message;

  int? _percent;
  int? get percent => _$this._percent;
  set percent(int? percent) => _$this._percent = percent;

  JsonObject? _tokenUsage;
  JsonObject? get tokenUsage => _$this._tokenUsage;
  set tokenUsage(JsonObject? tokenUsage) => _$this._tokenUsage = tokenUsage;

  String? _kind;
  String? get kind => _$this._kind;
  set kind(String? kind) => _$this._kind = kind;

  CheckpointBuilder() {
    Checkpoint._defaults(this);
  }

  CheckpointBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _taskId = $v.taskId;
      _attemptNumber = $v.attemptNumber;
      _sessionId = $v.sessionId;
      _timestamp = $v.timestamp;
      _message = $v.message;
      _percent = $v.percent;
      _tokenUsage = $v.tokenUsage;
      _kind = $v.kind;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(Checkpoint other) {
    _$v = other as _$Checkpoint;
  }

  @override
  void update(void Function(CheckpointBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  Checkpoint build() => _build();

  _$Checkpoint _build() {
    final _$result = _$v ??
        _$Checkpoint._(
          id: BuiltValueNullFieldError.checkNotNull(id, r'Checkpoint', 'id'),
          taskId: BuiltValueNullFieldError.checkNotNull(
              taskId, r'Checkpoint', 'taskId'),
          attemptNumber: BuiltValueNullFieldError.checkNotNull(
              attemptNumber, r'Checkpoint', 'attemptNumber'),
          sessionId: BuiltValueNullFieldError.checkNotNull(
              sessionId, r'Checkpoint', 'sessionId'),
          timestamp: BuiltValueNullFieldError.checkNotNull(
              timestamp, r'Checkpoint', 'timestamp'),
          message: BuiltValueNullFieldError.checkNotNull(
              message, r'Checkpoint', 'message'),
          percent: percent,
          tokenUsage: tokenUsage,
          kind: BuiltValueNullFieldError.checkNotNull(
              kind, r'Checkpoint', 'kind'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
