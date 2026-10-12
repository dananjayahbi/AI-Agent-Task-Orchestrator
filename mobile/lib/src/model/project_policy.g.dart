// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'project_policy.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ProjectPolicy extends ProjectPolicy {
  @override
  final int leaseDurationMinutes;
  @override
  final int leaseMaxTotalMinutes;
  @override
  final LeaseExtensionModeEnum leaseExtensionMode;
  @override
  final int maxRetries;
  @override
  final int maxConcurrentTasks;
  @override
  final int autonomousDiffThresholdLines;
  @override
  final int auditorMinConfidence;
  @override
  final BuiltList<String> criticalPathGlobs;
  @override
  final BuiltList<String> migrationPathGlobs;
  @override
  final BuiltList<String> sensitiveConfigGlobs;
  @override
  final bool autoCompleteEnabled;
  @override
  final MergeStrategyEnum mergeStrategy;
  @override
  final String branchPrefix;
  @override
  final bool auditRequiredDefault;
  @override
  final int stalledAfterMinutes;

  factory _$ProjectPolicy([void Function(ProjectPolicyBuilder)? updates]) =>
      (ProjectPolicyBuilder()..update(updates))._build();

  _$ProjectPolicy._(
      {required this.leaseDurationMinutes,
      required this.leaseMaxTotalMinutes,
      required this.leaseExtensionMode,
      required this.maxRetries,
      required this.maxConcurrentTasks,
      required this.autonomousDiffThresholdLines,
      required this.auditorMinConfidence,
      required this.criticalPathGlobs,
      required this.migrationPathGlobs,
      required this.sensitiveConfigGlobs,
      required this.autoCompleteEnabled,
      required this.mergeStrategy,
      required this.branchPrefix,
      required this.auditRequiredDefault,
      required this.stalledAfterMinutes})
      : super._();
  @override
  ProjectPolicy rebuild(void Function(ProjectPolicyBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ProjectPolicyBuilder toBuilder() => ProjectPolicyBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ProjectPolicy &&
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
        stalledAfterMinutes == other.stalledAfterMinutes;
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
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ProjectPolicy')
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
          ..add('stalledAfterMinutes', stalledAfterMinutes))
        .toString();
  }
}

class ProjectPolicyBuilder
    implements Builder<ProjectPolicy, ProjectPolicyBuilder> {
  _$ProjectPolicy? _$v;

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

  ProjectPolicyBuilder() {
    ProjectPolicy._defaults(this);
  }

  ProjectPolicyBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _leaseDurationMinutes = $v.leaseDurationMinutes;
      _leaseMaxTotalMinutes = $v.leaseMaxTotalMinutes;
      _leaseExtensionMode = $v.leaseExtensionMode;
      _maxRetries = $v.maxRetries;
      _maxConcurrentTasks = $v.maxConcurrentTasks;
      _autonomousDiffThresholdLines = $v.autonomousDiffThresholdLines;
      _auditorMinConfidence = $v.auditorMinConfidence;
      _criticalPathGlobs = $v.criticalPathGlobs.toBuilder();
      _migrationPathGlobs = $v.migrationPathGlobs.toBuilder();
      _sensitiveConfigGlobs = $v.sensitiveConfigGlobs.toBuilder();
      _autoCompleteEnabled = $v.autoCompleteEnabled;
      _mergeStrategy = $v.mergeStrategy;
      _branchPrefix = $v.branchPrefix;
      _auditRequiredDefault = $v.auditRequiredDefault;
      _stalledAfterMinutes = $v.stalledAfterMinutes;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ProjectPolicy other) {
    _$v = other as _$ProjectPolicy;
  }

  @override
  void update(void Function(ProjectPolicyBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ProjectPolicy build() => _build();

  _$ProjectPolicy _build() {
    _$ProjectPolicy _$result;
    try {
      _$result = _$v ??
          _$ProjectPolicy._(
            leaseDurationMinutes: BuiltValueNullFieldError.checkNotNull(
                leaseDurationMinutes, r'ProjectPolicy', 'leaseDurationMinutes'),
            leaseMaxTotalMinutes: BuiltValueNullFieldError.checkNotNull(
                leaseMaxTotalMinutes, r'ProjectPolicy', 'leaseMaxTotalMinutes'),
            leaseExtensionMode: BuiltValueNullFieldError.checkNotNull(
                leaseExtensionMode, r'ProjectPolicy', 'leaseExtensionMode'),
            maxRetries: BuiltValueNullFieldError.checkNotNull(
                maxRetries, r'ProjectPolicy', 'maxRetries'),
            maxConcurrentTasks: BuiltValueNullFieldError.checkNotNull(
                maxConcurrentTasks, r'ProjectPolicy', 'maxConcurrentTasks'),
            autonomousDiffThresholdLines: BuiltValueNullFieldError.checkNotNull(
                autonomousDiffThresholdLines,
                r'ProjectPolicy',
                'autonomousDiffThresholdLines'),
            auditorMinConfidence: BuiltValueNullFieldError.checkNotNull(
                auditorMinConfidence, r'ProjectPolicy', 'auditorMinConfidence'),
            criticalPathGlobs: criticalPathGlobs.build(),
            migrationPathGlobs: migrationPathGlobs.build(),
            sensitiveConfigGlobs: sensitiveConfigGlobs.build(),
            autoCompleteEnabled: BuiltValueNullFieldError.checkNotNull(
                autoCompleteEnabled, r'ProjectPolicy', 'autoCompleteEnabled'),
            mergeStrategy: BuiltValueNullFieldError.checkNotNull(
                mergeStrategy, r'ProjectPolicy', 'mergeStrategy'),
            branchPrefix: BuiltValueNullFieldError.checkNotNull(
                branchPrefix, r'ProjectPolicy', 'branchPrefix'),
            auditRequiredDefault: BuiltValueNullFieldError.checkNotNull(
                auditRequiredDefault, r'ProjectPolicy', 'auditRequiredDefault'),
            stalledAfterMinutes: BuiltValueNullFieldError.checkNotNull(
                stalledAfterMinutes, r'ProjectPolicy', 'stalledAfterMinutes'),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'criticalPathGlobs';
        criticalPathGlobs.build();
        _$failedField = 'migrationPathGlobs';
        migrationPathGlobs.build();
        _$failedField = 'sensitiveConfigGlobs';
        sensitiveConfigGlobs.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'ProjectPolicy', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
