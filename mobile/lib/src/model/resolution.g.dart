// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'resolution.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$Resolution extends Resolution {
  @override
  final String id;
  @override
  final String taskId;
  @override
  final int attemptNumber;
  @override
  final String branchName;
  @override
  final String commitSha;
  @override
  final String executionSummary;
  @override
  final JsonObject? diffSummary;
  @override
  final BuiltList<String> changedFiles;
  @override
  final bool requiresHumanAttention;
  @override
  final String riskJustification;
  @override
  final String submittedBySession;
  @override
  final DateTime submittedAt;

  factory _$Resolution([void Function(ResolutionBuilder)? updates]) =>
      (ResolutionBuilder()..update(updates))._build();

  _$Resolution._(
      {required this.id,
      required this.taskId,
      required this.attemptNumber,
      required this.branchName,
      required this.commitSha,
      required this.executionSummary,
      this.diffSummary,
      required this.changedFiles,
      required this.requiresHumanAttention,
      required this.riskJustification,
      required this.submittedBySession,
      required this.submittedAt})
      : super._();
  @override
  Resolution rebuild(void Function(ResolutionBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ResolutionBuilder toBuilder() => ResolutionBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is Resolution &&
        id == other.id &&
        taskId == other.taskId &&
        attemptNumber == other.attemptNumber &&
        branchName == other.branchName &&
        commitSha == other.commitSha &&
        executionSummary == other.executionSummary &&
        diffSummary == other.diffSummary &&
        changedFiles == other.changedFiles &&
        requiresHumanAttention == other.requiresHumanAttention &&
        riskJustification == other.riskJustification &&
        submittedBySession == other.submittedBySession &&
        submittedAt == other.submittedAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, taskId.hashCode);
    _$hash = $jc(_$hash, attemptNumber.hashCode);
    _$hash = $jc(_$hash, branchName.hashCode);
    _$hash = $jc(_$hash, commitSha.hashCode);
    _$hash = $jc(_$hash, executionSummary.hashCode);
    _$hash = $jc(_$hash, diffSummary.hashCode);
    _$hash = $jc(_$hash, changedFiles.hashCode);
    _$hash = $jc(_$hash, requiresHumanAttention.hashCode);
    _$hash = $jc(_$hash, riskJustification.hashCode);
    _$hash = $jc(_$hash, submittedBySession.hashCode);
    _$hash = $jc(_$hash, submittedAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'Resolution')
          ..add('id', id)
          ..add('taskId', taskId)
          ..add('attemptNumber', attemptNumber)
          ..add('branchName', branchName)
          ..add('commitSha', commitSha)
          ..add('executionSummary', executionSummary)
          ..add('diffSummary', diffSummary)
          ..add('changedFiles', changedFiles)
          ..add('requiresHumanAttention', requiresHumanAttention)
          ..add('riskJustification', riskJustification)
          ..add('submittedBySession', submittedBySession)
          ..add('submittedAt', submittedAt))
        .toString();
  }
}

class ResolutionBuilder implements Builder<Resolution, ResolutionBuilder> {
  _$Resolution? _$v;

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

  String? _branchName;
  String? get branchName => _$this._branchName;
  set branchName(String? branchName) => _$this._branchName = branchName;

  String? _commitSha;
  String? get commitSha => _$this._commitSha;
  set commitSha(String? commitSha) => _$this._commitSha = commitSha;

  String? _executionSummary;
  String? get executionSummary => _$this._executionSummary;
  set executionSummary(String? executionSummary) =>
      _$this._executionSummary = executionSummary;

  JsonObject? _diffSummary;
  JsonObject? get diffSummary => _$this._diffSummary;
  set diffSummary(JsonObject? diffSummary) => _$this._diffSummary = diffSummary;

  ListBuilder<String>? _changedFiles;
  ListBuilder<String> get changedFiles =>
      _$this._changedFiles ??= ListBuilder<String>();
  set changedFiles(ListBuilder<String>? changedFiles) =>
      _$this._changedFiles = changedFiles;

  bool? _requiresHumanAttention;
  bool? get requiresHumanAttention => _$this._requiresHumanAttention;
  set requiresHumanAttention(bool? requiresHumanAttention) =>
      _$this._requiresHumanAttention = requiresHumanAttention;

  String? _riskJustification;
  String? get riskJustification => _$this._riskJustification;
  set riskJustification(String? riskJustification) =>
      _$this._riskJustification = riskJustification;

  String? _submittedBySession;
  String? get submittedBySession => _$this._submittedBySession;
  set submittedBySession(String? submittedBySession) =>
      _$this._submittedBySession = submittedBySession;

  DateTime? _submittedAt;
  DateTime? get submittedAt => _$this._submittedAt;
  set submittedAt(DateTime? submittedAt) => _$this._submittedAt = submittedAt;

  ResolutionBuilder() {
    Resolution._defaults(this);
  }

  ResolutionBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _taskId = $v.taskId;
      _attemptNumber = $v.attemptNumber;
      _branchName = $v.branchName;
      _commitSha = $v.commitSha;
      _executionSummary = $v.executionSummary;
      _diffSummary = $v.diffSummary;
      _changedFiles = $v.changedFiles.toBuilder();
      _requiresHumanAttention = $v.requiresHumanAttention;
      _riskJustification = $v.riskJustification;
      _submittedBySession = $v.submittedBySession;
      _submittedAt = $v.submittedAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(Resolution other) {
    _$v = other as _$Resolution;
  }

  @override
  void update(void Function(ResolutionBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  Resolution build() => _build();

  _$Resolution _build() {
    _$Resolution _$result;
    try {
      _$result = _$v ??
          _$Resolution._(
            id: BuiltValueNullFieldError.checkNotNull(id, r'Resolution', 'id'),
            taskId: BuiltValueNullFieldError.checkNotNull(
                taskId, r'Resolution', 'taskId'),
            attemptNumber: BuiltValueNullFieldError.checkNotNull(
                attemptNumber, r'Resolution', 'attemptNumber'),
            branchName: BuiltValueNullFieldError.checkNotNull(
                branchName, r'Resolution', 'branchName'),
            commitSha: BuiltValueNullFieldError.checkNotNull(
                commitSha, r'Resolution', 'commitSha'),
            executionSummary: BuiltValueNullFieldError.checkNotNull(
                executionSummary, r'Resolution', 'executionSummary'),
            diffSummary: diffSummary,
            changedFiles: changedFiles.build(),
            requiresHumanAttention: BuiltValueNullFieldError.checkNotNull(
                requiresHumanAttention,
                r'Resolution',
                'requiresHumanAttention'),
            riskJustification: BuiltValueNullFieldError.checkNotNull(
                riskJustification, r'Resolution', 'riskJustification'),
            submittedBySession: BuiltValueNullFieldError.checkNotNull(
                submittedBySession, r'Resolution', 'submittedBySession'),
            submittedAt: BuiltValueNullFieldError.checkNotNull(
                submittedAt, r'Resolution', 'submittedAt'),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'changedFiles';
        changedFiles.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'Resolution', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
