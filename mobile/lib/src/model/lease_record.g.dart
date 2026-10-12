// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'lease_record.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$LeaseRecord extends LeaseRecord {
  @override
  final String taskId;
  @override
  final String assignedAgent;
  @override
  final String sessionId;
  @override
  final String role;
  @override
  final int leaseGeneration;
  @override
  final DateTime? leaseAcquiredAt;
  @override
  final DateTime? leaseExpiresAt;
  @override
  final DateTime? leaseHardCapAt;
  @override
  final DateTime? lastCheckpoint;
  @override
  final int failureRetryCount;

  factory _$LeaseRecord([void Function(LeaseRecordBuilder)? updates]) =>
      (LeaseRecordBuilder()..update(updates))._build();

  _$LeaseRecord._(
      {required this.taskId,
      required this.assignedAgent,
      required this.sessionId,
      required this.role,
      required this.leaseGeneration,
      this.leaseAcquiredAt,
      this.leaseExpiresAt,
      this.leaseHardCapAt,
      this.lastCheckpoint,
      required this.failureRetryCount})
      : super._();
  @override
  LeaseRecord rebuild(void Function(LeaseRecordBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  LeaseRecordBuilder toBuilder() => LeaseRecordBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is LeaseRecord &&
        taskId == other.taskId &&
        assignedAgent == other.assignedAgent &&
        sessionId == other.sessionId &&
        role == other.role &&
        leaseGeneration == other.leaseGeneration &&
        leaseAcquiredAt == other.leaseAcquiredAt &&
        leaseExpiresAt == other.leaseExpiresAt &&
        leaseHardCapAt == other.leaseHardCapAt &&
        lastCheckpoint == other.lastCheckpoint &&
        failureRetryCount == other.failureRetryCount;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, taskId.hashCode);
    _$hash = $jc(_$hash, assignedAgent.hashCode);
    _$hash = $jc(_$hash, sessionId.hashCode);
    _$hash = $jc(_$hash, role.hashCode);
    _$hash = $jc(_$hash, leaseGeneration.hashCode);
    _$hash = $jc(_$hash, leaseAcquiredAt.hashCode);
    _$hash = $jc(_$hash, leaseExpiresAt.hashCode);
    _$hash = $jc(_$hash, leaseHardCapAt.hashCode);
    _$hash = $jc(_$hash, lastCheckpoint.hashCode);
    _$hash = $jc(_$hash, failureRetryCount.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'LeaseRecord')
          ..add('taskId', taskId)
          ..add('assignedAgent', assignedAgent)
          ..add('sessionId', sessionId)
          ..add('role', role)
          ..add('leaseGeneration', leaseGeneration)
          ..add('leaseAcquiredAt', leaseAcquiredAt)
          ..add('leaseExpiresAt', leaseExpiresAt)
          ..add('leaseHardCapAt', leaseHardCapAt)
          ..add('lastCheckpoint', lastCheckpoint)
          ..add('failureRetryCount', failureRetryCount))
        .toString();
  }
}

class LeaseRecordBuilder implements Builder<LeaseRecord, LeaseRecordBuilder> {
  _$LeaseRecord? _$v;

  String? _taskId;
  String? get taskId => _$this._taskId;
  set taskId(String? taskId) => _$this._taskId = taskId;

  String? _assignedAgent;
  String? get assignedAgent => _$this._assignedAgent;
  set assignedAgent(String? assignedAgent) =>
      _$this._assignedAgent = assignedAgent;

  String? _sessionId;
  String? get sessionId => _$this._sessionId;
  set sessionId(String? sessionId) => _$this._sessionId = sessionId;

  String? _role;
  String? get role => _$this._role;
  set role(String? role) => _$this._role = role;

  int? _leaseGeneration;
  int? get leaseGeneration => _$this._leaseGeneration;
  set leaseGeneration(int? leaseGeneration) =>
      _$this._leaseGeneration = leaseGeneration;

  DateTime? _leaseAcquiredAt;
  DateTime? get leaseAcquiredAt => _$this._leaseAcquiredAt;
  set leaseAcquiredAt(DateTime? leaseAcquiredAt) =>
      _$this._leaseAcquiredAt = leaseAcquiredAt;

  DateTime? _leaseExpiresAt;
  DateTime? get leaseExpiresAt => _$this._leaseExpiresAt;
  set leaseExpiresAt(DateTime? leaseExpiresAt) =>
      _$this._leaseExpiresAt = leaseExpiresAt;

  DateTime? _leaseHardCapAt;
  DateTime? get leaseHardCapAt => _$this._leaseHardCapAt;
  set leaseHardCapAt(DateTime? leaseHardCapAt) =>
      _$this._leaseHardCapAt = leaseHardCapAt;

  DateTime? _lastCheckpoint;
  DateTime? get lastCheckpoint => _$this._lastCheckpoint;
  set lastCheckpoint(DateTime? lastCheckpoint) =>
      _$this._lastCheckpoint = lastCheckpoint;

  int? _failureRetryCount;
  int? get failureRetryCount => _$this._failureRetryCount;
  set failureRetryCount(int? failureRetryCount) =>
      _$this._failureRetryCount = failureRetryCount;

  LeaseRecordBuilder() {
    LeaseRecord._defaults(this);
  }

  LeaseRecordBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _taskId = $v.taskId;
      _assignedAgent = $v.assignedAgent;
      _sessionId = $v.sessionId;
      _role = $v.role;
      _leaseGeneration = $v.leaseGeneration;
      _leaseAcquiredAt = $v.leaseAcquiredAt;
      _leaseExpiresAt = $v.leaseExpiresAt;
      _leaseHardCapAt = $v.leaseHardCapAt;
      _lastCheckpoint = $v.lastCheckpoint;
      _failureRetryCount = $v.failureRetryCount;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(LeaseRecord other) {
    _$v = other as _$LeaseRecord;
  }

  @override
  void update(void Function(LeaseRecordBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  LeaseRecord build() => _build();

  _$LeaseRecord _build() {
    final _$result = _$v ??
        _$LeaseRecord._(
          taskId: BuiltValueNullFieldError.checkNotNull(
              taskId, r'LeaseRecord', 'taskId'),
          assignedAgent: BuiltValueNullFieldError.checkNotNull(
              assignedAgent, r'LeaseRecord', 'assignedAgent'),
          sessionId: BuiltValueNullFieldError.checkNotNull(
              sessionId, r'LeaseRecord', 'sessionId'),
          role: BuiltValueNullFieldError.checkNotNull(
              role, r'LeaseRecord', 'role'),
          leaseGeneration: BuiltValueNullFieldError.checkNotNull(
              leaseGeneration, r'LeaseRecord', 'leaseGeneration'),
          leaseAcquiredAt: leaseAcquiredAt,
          leaseExpiresAt: leaseExpiresAt,
          leaseHardCapAt: leaseHardCapAt,
          lastCheckpoint: lastCheckpoint,
          failureRetryCount: BuiltValueNullFieldError.checkNotNull(
              failureRetryCount, r'LeaseRecord', 'failureRetryCount'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
