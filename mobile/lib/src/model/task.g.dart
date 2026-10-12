// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'task.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$Task extends Task {
  @override
  final String id;
  @override
  final String projectId;
  @override
  final String title;
  @override
  final String description;
  @override
  final BuiltList<String> acceptanceCriteria;
  @override
  final BuiltList<String> targetScope;
  @override
  final String testCommand;
  @override
  final PriorityEnum priority;
  @override
  final StateEnum state;
  @override
  final int version;
  @override
  final String? workerAgentId;
  @override
  final String? workerSessionId;
  @override
  final String? claimedRole;
  @override
  final DateTime? leaseAcquiredAt;
  @override
  final DateTime? leaseExpiresAt;
  @override
  final DateTime? lastCheckpointAt;
  @override
  final int failureRetryCount;
  @override
  final int attemptNumber;
  @override
  final bool auditRequired;
  @override
  final String? reviewReason;
  @override
  final String latestFeedback;
  @override
  final String mergeStatus;
  @override
  final DateTime? archivedAt;
  @override
  final String? createdBy;
  @override
  final DateTime createdAt;
  @override
  final DateTime updatedAt;
  @override
  final BuiltList<String> dependsOn;

  factory _$Task([void Function(TaskBuilder)? updates]) =>
      (TaskBuilder()..update(updates))._build();

  _$Task._(
      {required this.id,
      required this.projectId,
      required this.title,
      required this.description,
      required this.acceptanceCriteria,
      required this.targetScope,
      required this.testCommand,
      required this.priority,
      required this.state,
      required this.version,
      this.workerAgentId,
      this.workerSessionId,
      this.claimedRole,
      this.leaseAcquiredAt,
      this.leaseExpiresAt,
      this.lastCheckpointAt,
      required this.failureRetryCount,
      required this.attemptNumber,
      required this.auditRequired,
      this.reviewReason,
      required this.latestFeedback,
      required this.mergeStatus,
      this.archivedAt,
      this.createdBy,
      required this.createdAt,
      required this.updatedAt,
      required this.dependsOn})
      : super._();
  @override
  Task rebuild(void Function(TaskBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  TaskBuilder toBuilder() => TaskBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is Task &&
        id == other.id &&
        projectId == other.projectId &&
        title == other.title &&
        description == other.description &&
        acceptanceCriteria == other.acceptanceCriteria &&
        targetScope == other.targetScope &&
        testCommand == other.testCommand &&
        priority == other.priority &&
        state == other.state &&
        version == other.version &&
        workerAgentId == other.workerAgentId &&
        workerSessionId == other.workerSessionId &&
        claimedRole == other.claimedRole &&
        leaseAcquiredAt == other.leaseAcquiredAt &&
        leaseExpiresAt == other.leaseExpiresAt &&
        lastCheckpointAt == other.lastCheckpointAt &&
        failureRetryCount == other.failureRetryCount &&
        attemptNumber == other.attemptNumber &&
        auditRequired == other.auditRequired &&
        reviewReason == other.reviewReason &&
        latestFeedback == other.latestFeedback &&
        mergeStatus == other.mergeStatus &&
        archivedAt == other.archivedAt &&
        createdBy == other.createdBy &&
        createdAt == other.createdAt &&
        updatedAt == other.updatedAt &&
        dependsOn == other.dependsOn;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, projectId.hashCode);
    _$hash = $jc(_$hash, title.hashCode);
    _$hash = $jc(_$hash, description.hashCode);
    _$hash = $jc(_$hash, acceptanceCriteria.hashCode);
    _$hash = $jc(_$hash, targetScope.hashCode);
    _$hash = $jc(_$hash, testCommand.hashCode);
    _$hash = $jc(_$hash, priority.hashCode);
    _$hash = $jc(_$hash, state.hashCode);
    _$hash = $jc(_$hash, version.hashCode);
    _$hash = $jc(_$hash, workerAgentId.hashCode);
    _$hash = $jc(_$hash, workerSessionId.hashCode);
    _$hash = $jc(_$hash, claimedRole.hashCode);
    _$hash = $jc(_$hash, leaseAcquiredAt.hashCode);
    _$hash = $jc(_$hash, leaseExpiresAt.hashCode);
    _$hash = $jc(_$hash, lastCheckpointAt.hashCode);
    _$hash = $jc(_$hash, failureRetryCount.hashCode);
    _$hash = $jc(_$hash, attemptNumber.hashCode);
    _$hash = $jc(_$hash, auditRequired.hashCode);
    _$hash = $jc(_$hash, reviewReason.hashCode);
    _$hash = $jc(_$hash, latestFeedback.hashCode);
    _$hash = $jc(_$hash, mergeStatus.hashCode);
    _$hash = $jc(_$hash, archivedAt.hashCode);
    _$hash = $jc(_$hash, createdBy.hashCode);
    _$hash = $jc(_$hash, createdAt.hashCode);
    _$hash = $jc(_$hash, updatedAt.hashCode);
    _$hash = $jc(_$hash, dependsOn.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'Task')
          ..add('id', id)
          ..add('projectId', projectId)
          ..add('title', title)
          ..add('description', description)
          ..add('acceptanceCriteria', acceptanceCriteria)
          ..add('targetScope', targetScope)
          ..add('testCommand', testCommand)
          ..add('priority', priority)
          ..add('state', state)
          ..add('version', version)
          ..add('workerAgentId', workerAgentId)
          ..add('workerSessionId', workerSessionId)
          ..add('claimedRole', claimedRole)
          ..add('leaseAcquiredAt', leaseAcquiredAt)
          ..add('leaseExpiresAt', leaseExpiresAt)
          ..add('lastCheckpointAt', lastCheckpointAt)
          ..add('failureRetryCount', failureRetryCount)
          ..add('attemptNumber', attemptNumber)
          ..add('auditRequired', auditRequired)
          ..add('reviewReason', reviewReason)
          ..add('latestFeedback', latestFeedback)
          ..add('mergeStatus', mergeStatus)
          ..add('archivedAt', archivedAt)
          ..add('createdBy', createdBy)
          ..add('createdAt', createdAt)
          ..add('updatedAt', updatedAt)
          ..add('dependsOn', dependsOn))
        .toString();
  }
}

class TaskBuilder implements Builder<Task, TaskBuilder> {
  _$Task? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _projectId;
  String? get projectId => _$this._projectId;
  set projectId(String? projectId) => _$this._projectId = projectId;

  String? _title;
  String? get title => _$this._title;
  set title(String? title) => _$this._title = title;

  String? _description;
  String? get description => _$this._description;
  set description(String? description) => _$this._description = description;

  ListBuilder<String>? _acceptanceCriteria;
  ListBuilder<String> get acceptanceCriteria =>
      _$this._acceptanceCriteria ??= ListBuilder<String>();
  set acceptanceCriteria(ListBuilder<String>? acceptanceCriteria) =>
      _$this._acceptanceCriteria = acceptanceCriteria;

  ListBuilder<String>? _targetScope;
  ListBuilder<String> get targetScope =>
      _$this._targetScope ??= ListBuilder<String>();
  set targetScope(ListBuilder<String>? targetScope) =>
      _$this._targetScope = targetScope;

  String? _testCommand;
  String? get testCommand => _$this._testCommand;
  set testCommand(String? testCommand) => _$this._testCommand = testCommand;

  PriorityEnum? _priority;
  PriorityEnum? get priority => _$this._priority;
  set priority(PriorityEnum? priority) => _$this._priority = priority;

  StateEnum? _state;
  StateEnum? get state => _$this._state;
  set state(StateEnum? state) => _$this._state = state;

  int? _version;
  int? get version => _$this._version;
  set version(int? version) => _$this._version = version;

  String? _workerAgentId;
  String? get workerAgentId => _$this._workerAgentId;
  set workerAgentId(String? workerAgentId) =>
      _$this._workerAgentId = workerAgentId;

  String? _workerSessionId;
  String? get workerSessionId => _$this._workerSessionId;
  set workerSessionId(String? workerSessionId) =>
      _$this._workerSessionId = workerSessionId;

  String? _claimedRole;
  String? get claimedRole => _$this._claimedRole;
  set claimedRole(String? claimedRole) => _$this._claimedRole = claimedRole;

  DateTime? _leaseAcquiredAt;
  DateTime? get leaseAcquiredAt => _$this._leaseAcquiredAt;
  set leaseAcquiredAt(DateTime? leaseAcquiredAt) =>
      _$this._leaseAcquiredAt = leaseAcquiredAt;

  DateTime? _leaseExpiresAt;
  DateTime? get leaseExpiresAt => _$this._leaseExpiresAt;
  set leaseExpiresAt(DateTime? leaseExpiresAt) =>
      _$this._leaseExpiresAt = leaseExpiresAt;

  DateTime? _lastCheckpointAt;
  DateTime? get lastCheckpointAt => _$this._lastCheckpointAt;
  set lastCheckpointAt(DateTime? lastCheckpointAt) =>
      _$this._lastCheckpointAt = lastCheckpointAt;

  int? _failureRetryCount;
  int? get failureRetryCount => _$this._failureRetryCount;
  set failureRetryCount(int? failureRetryCount) =>
      _$this._failureRetryCount = failureRetryCount;

  int? _attemptNumber;
  int? get attemptNumber => _$this._attemptNumber;
  set attemptNumber(int? attemptNumber) =>
      _$this._attemptNumber = attemptNumber;

  bool? _auditRequired;
  bool? get auditRequired => _$this._auditRequired;
  set auditRequired(bool? auditRequired) =>
      _$this._auditRequired = auditRequired;

  String? _reviewReason;
  String? get reviewReason => _$this._reviewReason;
  set reviewReason(String? reviewReason) => _$this._reviewReason = reviewReason;

  String? _latestFeedback;
  String? get latestFeedback => _$this._latestFeedback;
  set latestFeedback(String? latestFeedback) =>
      _$this._latestFeedback = latestFeedback;

  String? _mergeStatus;
  String? get mergeStatus => _$this._mergeStatus;
  set mergeStatus(String? mergeStatus) => _$this._mergeStatus = mergeStatus;

  DateTime? _archivedAt;
  DateTime? get archivedAt => _$this._archivedAt;
  set archivedAt(DateTime? archivedAt) => _$this._archivedAt = archivedAt;

  String? _createdBy;
  String? get createdBy => _$this._createdBy;
  set createdBy(String? createdBy) => _$this._createdBy = createdBy;

  DateTime? _createdAt;
  DateTime? get createdAt => _$this._createdAt;
  set createdAt(DateTime? createdAt) => _$this._createdAt = createdAt;

  DateTime? _updatedAt;
  DateTime? get updatedAt => _$this._updatedAt;
  set updatedAt(DateTime? updatedAt) => _$this._updatedAt = updatedAt;

  ListBuilder<String>? _dependsOn;
  ListBuilder<String> get dependsOn =>
      _$this._dependsOn ??= ListBuilder<String>();
  set dependsOn(ListBuilder<String>? dependsOn) =>
      _$this._dependsOn = dependsOn;

  TaskBuilder() {
    Task._defaults(this);
  }

  TaskBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _projectId = $v.projectId;
      _title = $v.title;
      _description = $v.description;
      _acceptanceCriteria = $v.acceptanceCriteria.toBuilder();
      _targetScope = $v.targetScope.toBuilder();
      _testCommand = $v.testCommand;
      _priority = $v.priority;
      _state = $v.state;
      _version = $v.version;
      _workerAgentId = $v.workerAgentId;
      _workerSessionId = $v.workerSessionId;
      _claimedRole = $v.claimedRole;
      _leaseAcquiredAt = $v.leaseAcquiredAt;
      _leaseExpiresAt = $v.leaseExpiresAt;
      _lastCheckpointAt = $v.lastCheckpointAt;
      _failureRetryCount = $v.failureRetryCount;
      _attemptNumber = $v.attemptNumber;
      _auditRequired = $v.auditRequired;
      _reviewReason = $v.reviewReason;
      _latestFeedback = $v.latestFeedback;
      _mergeStatus = $v.mergeStatus;
      _archivedAt = $v.archivedAt;
      _createdBy = $v.createdBy;
      _createdAt = $v.createdAt;
      _updatedAt = $v.updatedAt;
      _dependsOn = $v.dependsOn.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(Task other) {
    _$v = other as _$Task;
  }

  @override
  void update(void Function(TaskBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  Task build() => _build();

  _$Task _build() {
    _$Task _$result;
    try {
      _$result = _$v ??
          _$Task._(
            id: BuiltValueNullFieldError.checkNotNull(id, r'Task', 'id'),
            projectId: BuiltValueNullFieldError.checkNotNull(
                projectId, r'Task', 'projectId'),
            title:
                BuiltValueNullFieldError.checkNotNull(title, r'Task', 'title'),
            description: BuiltValueNullFieldError.checkNotNull(
                description, r'Task', 'description'),
            acceptanceCriteria: acceptanceCriteria.build(),
            targetScope: targetScope.build(),
            testCommand: BuiltValueNullFieldError.checkNotNull(
                testCommand, r'Task', 'testCommand'),
            priority: BuiltValueNullFieldError.checkNotNull(
                priority, r'Task', 'priority'),
            state:
                BuiltValueNullFieldError.checkNotNull(state, r'Task', 'state'),
            version: BuiltValueNullFieldError.checkNotNull(
                version, r'Task', 'version'),
            workerAgentId: workerAgentId,
            workerSessionId: workerSessionId,
            claimedRole: claimedRole,
            leaseAcquiredAt: leaseAcquiredAt,
            leaseExpiresAt: leaseExpiresAt,
            lastCheckpointAt: lastCheckpointAt,
            failureRetryCount: BuiltValueNullFieldError.checkNotNull(
                failureRetryCount, r'Task', 'failureRetryCount'),
            attemptNumber: BuiltValueNullFieldError.checkNotNull(
                attemptNumber, r'Task', 'attemptNumber'),
            auditRequired: BuiltValueNullFieldError.checkNotNull(
                auditRequired, r'Task', 'auditRequired'),
            reviewReason: reviewReason,
            latestFeedback: BuiltValueNullFieldError.checkNotNull(
                latestFeedback, r'Task', 'latestFeedback'),
            mergeStatus: BuiltValueNullFieldError.checkNotNull(
                mergeStatus, r'Task', 'mergeStatus'),
            archivedAt: archivedAt,
            createdBy: createdBy,
            createdAt: BuiltValueNullFieldError.checkNotNull(
                createdAt, r'Task', 'createdAt'),
            updatedAt: BuiltValueNullFieldError.checkNotNull(
                updatedAt, r'Task', 'updatedAt'),
            dependsOn: dependsOn.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'acceptanceCriteria';
        acceptanceCriteria.build();
        _$failedField = 'targetScope';
        targetScope.build();

        _$failedField = 'dependsOn';
        dependsOn.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(r'Task', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
