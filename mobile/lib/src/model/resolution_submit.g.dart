// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'resolution_submit.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ResolutionSubmit extends ResolutionSubmit {
  @override
  final String sessionId;
  @override
  final int leaseGeneration;
  @override
  final String gitBranch;
  @override
  final String commitSha;
  @override
  final String executionSummary;
  @override
  final bool? requiresHumanAttention;
  @override
  final String? riskJustification;
  @override
  final String patch_;
  @override
  final BuiltList<String>? changedFiles;
  @override
  final BuiltMap<String, JsonObject?>? diffSummary;

  factory _$ResolutionSubmit(
          [void Function(ResolutionSubmitBuilder)? updates]) =>
      (ResolutionSubmitBuilder()..update(updates))._build();

  _$ResolutionSubmit._(
      {required this.sessionId,
      required this.leaseGeneration,
      required this.gitBranch,
      required this.commitSha,
      required this.executionSummary,
      this.requiresHumanAttention,
      this.riskJustification,
      required this.patch_,
      this.changedFiles,
      this.diffSummary})
      : super._();
  @override
  ResolutionSubmit rebuild(void Function(ResolutionSubmitBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ResolutionSubmitBuilder toBuilder() =>
      ResolutionSubmitBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ResolutionSubmit &&
        sessionId == other.sessionId &&
        leaseGeneration == other.leaseGeneration &&
        gitBranch == other.gitBranch &&
        commitSha == other.commitSha &&
        executionSummary == other.executionSummary &&
        requiresHumanAttention == other.requiresHumanAttention &&
        riskJustification == other.riskJustification &&
        patch_ == other.patch_ &&
        changedFiles == other.changedFiles &&
        diffSummary == other.diffSummary;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, sessionId.hashCode);
    _$hash = $jc(_$hash, leaseGeneration.hashCode);
    _$hash = $jc(_$hash, gitBranch.hashCode);
    _$hash = $jc(_$hash, commitSha.hashCode);
    _$hash = $jc(_$hash, executionSummary.hashCode);
    _$hash = $jc(_$hash, requiresHumanAttention.hashCode);
    _$hash = $jc(_$hash, riskJustification.hashCode);
    _$hash = $jc(_$hash, patch_.hashCode);
    _$hash = $jc(_$hash, changedFiles.hashCode);
    _$hash = $jc(_$hash, diffSummary.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ResolutionSubmit')
          ..add('sessionId', sessionId)
          ..add('leaseGeneration', leaseGeneration)
          ..add('gitBranch', gitBranch)
          ..add('commitSha', commitSha)
          ..add('executionSummary', executionSummary)
          ..add('requiresHumanAttention', requiresHumanAttention)
          ..add('riskJustification', riskJustification)
          ..add('patch_', patch_)
          ..add('changedFiles', changedFiles)
          ..add('diffSummary', diffSummary))
        .toString();
  }
}

class ResolutionSubmitBuilder
    implements Builder<ResolutionSubmit, ResolutionSubmitBuilder> {
  _$ResolutionSubmit? _$v;

  String? _sessionId;
  String? get sessionId => _$this._sessionId;
  set sessionId(String? sessionId) => _$this._sessionId = sessionId;

  int? _leaseGeneration;
  int? get leaseGeneration => _$this._leaseGeneration;
  set leaseGeneration(int? leaseGeneration) =>
      _$this._leaseGeneration = leaseGeneration;

  String? _gitBranch;
  String? get gitBranch => _$this._gitBranch;
  set gitBranch(String? gitBranch) => _$this._gitBranch = gitBranch;

  String? _commitSha;
  String? get commitSha => _$this._commitSha;
  set commitSha(String? commitSha) => _$this._commitSha = commitSha;

  String? _executionSummary;
  String? get executionSummary => _$this._executionSummary;
  set executionSummary(String? executionSummary) =>
      _$this._executionSummary = executionSummary;

  bool? _requiresHumanAttention;
  bool? get requiresHumanAttention => _$this._requiresHumanAttention;
  set requiresHumanAttention(bool? requiresHumanAttention) =>
      _$this._requiresHumanAttention = requiresHumanAttention;

  String? _riskJustification;
  String? get riskJustification => _$this._riskJustification;
  set riskJustification(String? riskJustification) =>
      _$this._riskJustification = riskJustification;

  String? _patch_;
  String? get patch_ => _$this._patch_;
  set patch_(String? patch_) => _$this._patch_ = patch_;

  ListBuilder<String>? _changedFiles;
  ListBuilder<String> get changedFiles =>
      _$this._changedFiles ??= ListBuilder<String>();
  set changedFiles(ListBuilder<String>? changedFiles) =>
      _$this._changedFiles = changedFiles;

  MapBuilder<String, JsonObject?>? _diffSummary;
  MapBuilder<String, JsonObject?> get diffSummary =>
      _$this._diffSummary ??= MapBuilder<String, JsonObject?>();
  set diffSummary(MapBuilder<String, JsonObject?>? diffSummary) =>
      _$this._diffSummary = diffSummary;

  ResolutionSubmitBuilder() {
    ResolutionSubmit._defaults(this);
  }

  ResolutionSubmitBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _sessionId = $v.sessionId;
      _leaseGeneration = $v.leaseGeneration;
      _gitBranch = $v.gitBranch;
      _commitSha = $v.commitSha;
      _executionSummary = $v.executionSummary;
      _requiresHumanAttention = $v.requiresHumanAttention;
      _riskJustification = $v.riskJustification;
      _patch_ = $v.patch_;
      _changedFiles = $v.changedFiles?.toBuilder();
      _diffSummary = $v.diffSummary?.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ResolutionSubmit other) {
    _$v = other as _$ResolutionSubmit;
  }

  @override
  void update(void Function(ResolutionSubmitBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ResolutionSubmit build() => _build();

  _$ResolutionSubmit _build() {
    _$ResolutionSubmit _$result;
    try {
      _$result = _$v ??
          _$ResolutionSubmit._(
            sessionId: BuiltValueNullFieldError.checkNotNull(
                sessionId, r'ResolutionSubmit', 'sessionId'),
            leaseGeneration: BuiltValueNullFieldError.checkNotNull(
                leaseGeneration, r'ResolutionSubmit', 'leaseGeneration'),
            gitBranch: BuiltValueNullFieldError.checkNotNull(
                gitBranch, r'ResolutionSubmit', 'gitBranch'),
            commitSha: BuiltValueNullFieldError.checkNotNull(
                commitSha, r'ResolutionSubmit', 'commitSha'),
            executionSummary: BuiltValueNullFieldError.checkNotNull(
                executionSummary, r'ResolutionSubmit', 'executionSummary'),
            requiresHumanAttention: requiresHumanAttention,
            riskJustification: riskJustification,
            patch_: BuiltValueNullFieldError.checkNotNull(
                patch_, r'ResolutionSubmit', 'patch_'),
            changedFiles: _changedFiles?.build(),
            diffSummary: _diffSummary?.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'changedFiles';
        _changedFiles?.build();
        _$failedField = 'diffSummary';
        _diffSummary?.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'ResolutionSubmit', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
