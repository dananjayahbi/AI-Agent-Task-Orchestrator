// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'patched_project_policy.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$PatchedProjectPolicy extends PatchedProjectPolicy {
  @override
  final int? leaseDurationMinutes;
  @override
  final int? leaseMaxTotalMinutes;
  @override
  final LeaseExtensionModeEnum? leaseExtensionMode;
  @override
  final int? maxRetries;
  @override
  final int? maxConcurrentTasks;
  @override
  final int? autonomousDiffThresholdLines;
  @override
  final int? auditorMinConfidence;
  @override
  final BuiltList<String>? criticalPathGlobs;
  @override
  final BuiltList<String>? migrationPathGlobs;
  @override
  final BuiltList<String>? sensitiveConfigGlobs;
  @override
  final bool? autoCompleteEnabled;
  @override
  final MergeStrategyEnum? mergeStrategy;
  @override
  final String? branchPrefix;
  @override
  final bool? auditRequiredDefault;
  @override
  final int? stalledAfterMinutes;
  @override
  final PolicyPresetEnum? policyPreset;

  factory _$PatchedProjectPolicy(
          [void Function(PatchedProjectPolicyBuilder)? updates]) =>
      (PatchedProjectPolicyBuilder()..update(updates))._build();

  _$PatchedProjectPolicy._(
      {this.leaseDurationMinutes,
      this.leaseMaxTotalMinutes,
      this.leaseExtensionMode,
      this.maxRetries,
      this.maxConcurrentTasks,
      this.autonomousDiffThresholdLines,
      this.auditorMinConfidence,
      this.criticalPathGlobs,
      this.migrationPathGlobs,
      this.sensitiveConfigGlobs,
      this.autoCompleteEnabled,
      this.mergeStrategy,
      this.branchPrefix,
      this.auditRequiredDefault,
      this.stalledAfterMinutes,
      this.policyPreset})
      : super._();
  @override
  PatchedProjectPolicy rebuild(
          void Function(PatchedProjectPolicyBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  PatchedProjectPolicyBuilder toBuilder() =>
      PatchedProjectPolicyBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is PatchedProjectPolicy &&
        leaseDurationMinutes == other.leaseDurationMinutes &&
        leaseMaxTotalMinutes == other.leaseMaxTotalMinutes &&
        leaseExtensionMode == other.leaseExtensionMode &&
        maxRetries == other.maxRetries &&
        maxConcurrentTasks == other.maxConcurrentTasks &&
        autonomousDiffThresholdLines == other.autonomousDiffThresholdLines &&
        auditorMinConfidence == other.auditorMinConfidence &&
        criticalPathGlobs == other.criticalPathGlobs &&
        migrationPathGlobs == other.migrationPathGlobs &&
        sensitiveConfigGlobs == other.sensitiveConfigGlobs &&
        autoCompleteEnabled == other.autoCompleteEnabled &&
        mergeStrategy == other.mergeStrategy &&
        branchPrefix == other.branchPrefix &&
        auditRequiredDefault == other.auditRequiredDefault &&
        stalledAfterMinutes == other.stalledAfterMinutes &&
        policyPreset == other.policyPreset;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, leaseDurationMinutes.hashCode);
    _$hash = $jc(_$hash, leaseMaxTotalMinutes.hashCode);
    _$hash = $jc(_$hash, leaseExtensionMode.hashCode);
    _$hash = $jc(_$hash, maxRetries.hashCode);
    _$hash = $jc(_$hash, maxConcurrentTasks.hashCode);
    _$hash = $jc(_$hash, autonomousDiffThresholdLines.hashCode);
    _$hash = $jc(_$hash, auditorMinConfidence.hashCode);
    _$hash = $jc(_$hash, criticalPathGlobs.hashCode);
    _$hash = $jc(_$hash, migrationPathGlobs.hashCode);
    _$hash = $jc(_$hash, sensitiveConfigGlobs.hashCode);
    _$hash = $jc(_$hash, autoCompleteEnabled.hashCode);
    _$hash = $jc(_$hash, mergeStrategy.hashCode);
    _$hash = $jc(_$hash, branchPrefix.hashCode);
    _$hash = $jc(_$hash, auditRequiredDefault.hashCode);
    _$hash = $jc(_$hash, stalledAfterMinutes.hashCode);
    _$hash = $jc(_$hash, policyPreset.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'PatchedProjectPolicy')
          ..add('leaseDurationMinutes', leaseDurationMinutes)
          ..add('leaseMaxTotalMinutes', leaseMaxTotalMinutes)
          ..add('leaseExtensionMode', leaseExtensionMode)
          ..add('maxRetries', maxRetries)
          ..add('maxConcurrentTasks', maxConcurrentTasks)
          ..add('autonomousDiffThresholdLines', autonomousDiffThresholdLines)
          ..add('auditorMinConfidence', auditorMinConfidence)
          ..add('criticalPathGlobs', criticalPathGlobs)
          ..add('migrationPathGlobs', migrationPathGlobs)
          ..add('sensitiveConfigGlobs', sensitiveConfigGlobs)
          ..add('autoCompleteEnabled', autoCompleteEnabled)
          ..add('mergeStrategy', mergeStrategy)
          ..add('branchPrefix', branchPrefix)
          ..add('auditRequiredDefault', auditRequiredDefault)
          ..add('stalledAfterMinutes', stalledAfterMinutes)
          ..add('policyPreset', policyPreset))
        .toString();
  }
}

class PatchedProjectPolicyBuilder
    implements Builder<PatchedProjectPolicy, PatchedProjectPolicyBuilder> {
  _$PatchedProjectPolicy? _$v;

  int? _leaseDurationMinutes;
  int? get leaseDurationMinutes => _$this._leaseDurationMinutes;
  set leaseDurationMinutes(int? leaseDurationMinutes) =>
      _$this._leaseDurationMinutes = leaseDurationMinutes;

  int? _leaseMaxTotalMinutes;
  int? get leaseMaxTotalMinutes => _$this._leaseMaxTotalMinutes;
  set leaseMaxTotalMinutes(int? leaseMaxTotalMinutes) =>
      _$this._leaseMaxTotalMinutes = leaseMaxTotalMinutes;

  LeaseExtensionModeEnum? _leaseExtensionMode;
  LeaseExtensionModeEnum? get leaseExtensionMode => _$this._leaseExtensionMode;
  set leaseExtensionMode(LeaseExtensionModeEnum? leaseExtensionMode) =>
      _$this._leaseExtensionMode = leaseExtensionMode;

  int? _maxRetries;
  int? get maxRetries => _$this._maxRetries;
  set maxRetries(int? maxRetries) => _$this._maxRetries = maxRetries;

  int? _maxConcurrentTasks;
  int? get maxConcurrentTasks => _$this._maxConcurrentTasks;
  set maxConcurrentTasks(int? maxConcurrentTasks) =>
      _$this._maxConcurrentTasks = maxConcurrentTasks;

  int? _autonomousDiffThresholdLines;
  int? get autonomousDiffThresholdLines => _$this._autonomousDiffThresholdLines;
  set autonomousDiffThresholdLines(int? autonomousDiffThresholdLines) =>
      _$this._autonomousDiffThresholdLines = autonomousDiffThresholdLines;

  int? _auditorMinConfidence;
  int? get auditorMinConfidence => _$this._auditorMinConfidence;
  set auditorMinConfidence(int? auditorMinConfidence) =>
      _$this._auditorMinConfidence = auditorMinConfidence;

  ListBuilder<String>? _criticalPathGlobs;
  ListBuilder<String> get criticalPathGlobs =>
      _$this._criticalPathGlobs ??= ListBuilder<String>();
  set criticalPathGlobs(ListBuilder<String>? criticalPathGlobs) =>
      _$this._criticalPathGlobs = criticalPathGlobs;

  ListBuilder<String>? _migrationPathGlobs;
  ListBuilder<String> get migrationPathGlobs =>
      _$this._migrationPathGlobs ??= ListBuilder<String>();
  set migrationPathGlobs(ListBuilder<String>? migrationPathGlobs) =>
      _$this._migrationPathGlobs = migrationPathGlobs;

  ListBuilder<String>? _sensitiveConfigGlobs;
  ListBuilder<String> get sensitiveConfigGlobs =>
      _$this._sensitiveConfigGlobs ??= ListBuilder<String>();
  set sensitiveConfigGlobs(ListBuilder<String>? sensitiveConfigGlobs) =>
      _$this._sensitiveConfigGlobs = sensitiveConfigGlobs;

  bool? _autoCompleteEnabled;
  bool? get autoCompleteEnabled => _$this._autoCompleteEnabled;
  set autoCompleteEnabled(bool? autoCompleteEnabled) =>
      _$this._autoCompleteEnabled = autoCompleteEnabled;

  MergeStrategyEnum? _mergeStrategy;
  MergeStrategyEnum? get mergeStrategy => _$this._mergeStrategy;
  set mergeStrategy(MergeStrategyEnum? mergeStrategy) =>
      _$this._mergeStrategy = mergeStrategy;

  String? _branchPrefix;
  String? get branchPrefix => _$this._branchPrefix;
  set branchPrefix(String? branchPrefix) => _$this._branchPrefix = branchPrefix;

  bool? _auditRequiredDefault;
  bool? get auditRequiredDefault => _$this._auditRequiredDefault;
  set auditRequiredDefault(bool? auditRequiredDefault) =>
      _$this._auditRequiredDefault = auditRequiredDefault;

  int? _stalledAfterMinutes;
  int? get stalledAfterMinutes => _$this._stalledAfterMinutes;
  set stalledAfterMinutes(int? stalledAfterMinutes) =>
      _$this._stalledAfterMinutes = stalledAfterMinutes;

  PolicyPresetEnum? _policyPreset;
  PolicyPresetEnum? get policyPreset => _$this._policyPreset;
  set policyPreset(PolicyPresetEnum? policyPreset) =>
      _$this._policyPreset = policyPreset;

  PatchedProjectPolicyBuilder() {
    PatchedProjectPolicy._defaults(this);
  }

  PatchedProjectPolicyBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _leaseDurationMinutes = $v.leaseDurationMinutes;
      _leaseMaxTotalMinutes = $v.leaseMaxTotalMinutes;
      _leaseExtensionMode = $v.leaseExtensionMode;
      _maxRetries = $v.maxRetries;
      _maxConcurrentTasks = $v.maxConcurrentTasks;
      _autonomousDiffThresholdLines = $v.autonomousDiffThresholdLines;
      _auditorMinConfidence = $v.auditorMinConfidence;
      _criticalPathGlobs = $v.criticalPathGlobs?.toBuilder();
      _migrationPathGlobs = $v.migrationPathGlobs?.toBuilder();
      _sensitiveConfigGlobs = $v.sensitiveConfigGlobs?.toBuilder();
      _autoCompleteEnabled = $v.autoCompleteEnabled;
      _mergeStrategy = $v.mergeStrategy;
      _branchPrefix = $v.branchPrefix;
      _auditRequiredDefault = $v.auditRequiredDefault;
      _stalledAfterMinutes = $v.stalledAfterMinutes;
      _policyPreset = $v.policyPreset;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(PatchedProjectPolicy other) {
    _$v = other as _$PatchedProjectPolicy;
  }

  @override
  void update(void Function(PatchedProjectPolicyBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  PatchedProjectPolicy build() => _build();

  _$PatchedProjectPolicy _build() {
    _$PatchedProjectPolicy _$result;
    try {
      _$result = _$v ??
          _$PatchedProjectPolicy._(
            leaseDurationMinutes: leaseDurationMinutes,
            leaseMaxTotalMinutes: leaseMaxTotalMinutes,
            leaseExtensionMode: leaseExtensionMode,
            maxRetries: maxRetries,
            maxConcurrentTasks: maxConcurrentTasks,
            autonomousDiffThresholdLines: autonomousDiffThresholdLines,
            auditorMinConfidence: auditorMinConfidence,
            criticalPathGlobs: _criticalPathGlobs?.build(),
            migrationPathGlobs: _migrationPathGlobs?.build(),
            sensitiveConfigGlobs: _sensitiveConfigGlobs?.build(),
            autoCompleteEnabled: autoCompleteEnabled,
            mergeStrategy: mergeStrategy,
            branchPrefix: branchPrefix,
            auditRequiredDefault: auditRequiredDefault,
            stalledAfterMinutes: stalledAfterMinutes,
            policyPreset: policyPreset,
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'criticalPathGlobs';
        _criticalPathGlobs?.build();
        _$failedField = 'migrationPathGlobs';
        _migrationPathGlobs?.build();
        _$failedField = 'sensitiveConfigGlobs';
        _sensitiveConfigGlobs?.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'PatchedProjectPolicy', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
