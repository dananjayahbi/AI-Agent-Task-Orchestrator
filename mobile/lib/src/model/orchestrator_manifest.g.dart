// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'orchestrator_manifest.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$OrchestratorManifest extends OrchestratorManifest {
  @override
  final String dollarSchema;
  @override
  final int schemaVersion;
  @override
  final String projectId;
  @override
  final String projectName;
  @override
  final String orchestratorApi;
  @override
  final String defaultBranch;
  @override
  final String autoBranchPrefix;
  @override
  final bool auditRequiredDefault;
  @override
  final AgentHints? agentHints;

  factory _$OrchestratorManifest(
          [void Function(OrchestratorManifestBuilder)? updates]) =>
      (OrchestratorManifestBuilder()..update(updates))._build();

  _$OrchestratorManifest._(
      {required this.dollarSchema,
      required this.schemaVersion,
      required this.projectId,
      required this.projectName,
      required this.orchestratorApi,
      required this.defaultBranch,
      required this.autoBranchPrefix,
      required this.auditRequiredDefault,
      this.agentHints})
      : super._();
  @override
  OrchestratorManifest rebuild(
          void Function(OrchestratorManifestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  OrchestratorManifestBuilder toBuilder() =>
      OrchestratorManifestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is OrchestratorManifest &&
        dollarSchema == other.dollarSchema &&
        schemaVersion == other.schemaVersion &&
        projectId == other.projectId &&
        projectName == other.projectName &&
        orchestratorApi == other.orchestratorApi &&
        defaultBranch == other.defaultBranch &&
        autoBranchPrefix == other.autoBranchPrefix &&
        auditRequiredDefault == other.auditRequiredDefault &&
        agentHints == other.agentHints;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, dollarSchema.hashCode);
    _$hash = $jc(_$hash, schemaVersion.hashCode);
    _$hash = $jc(_$hash, projectId.hashCode);
    _$hash = $jc(_$hash, projectName.hashCode);
    _$hash = $jc(_$hash, orchestratorApi.hashCode);
    _$hash = $jc(_$hash, defaultBranch.hashCode);
    _$hash = $jc(_$hash, autoBranchPrefix.hashCode);
    _$hash = $jc(_$hash, auditRequiredDefault.hashCode);
    _$hash = $jc(_$hash, agentHints.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'OrchestratorManifest')
          ..add('dollarSchema', dollarSchema)
          ..add('schemaVersion', schemaVersion)
          ..add('projectId', projectId)
          ..add('projectName', projectName)
          ..add('orchestratorApi', orchestratorApi)
          ..add('defaultBranch', defaultBranch)
          ..add('autoBranchPrefix', autoBranchPrefix)
          ..add('auditRequiredDefault', auditRequiredDefault)
          ..add('agentHints', agentHints))
        .toString();
  }
}

class OrchestratorManifestBuilder
    implements Builder<OrchestratorManifest, OrchestratorManifestBuilder> {
  _$OrchestratorManifest? _$v;

  String? _dollarSchema;
  String? get dollarSchema => _$this._dollarSchema;
  set dollarSchema(String? dollarSchema) => _$this._dollarSchema = dollarSchema;

  int? _schemaVersion;
  int? get schemaVersion => _$this._schemaVersion;
  set schemaVersion(int? schemaVersion) =>
      _$this._schemaVersion = schemaVersion;

  String? _projectId;
  String? get projectId => _$this._projectId;
  set projectId(String? projectId) => _$this._projectId = projectId;

  String? _projectName;
  String? get projectName => _$this._projectName;
  set projectName(String? projectName) => _$this._projectName = projectName;

  String? _orchestratorApi;
  String? get orchestratorApi => _$this._orchestratorApi;
  set orchestratorApi(String? orchestratorApi) =>
      _$this._orchestratorApi = orchestratorApi;

  String? _defaultBranch;
  String? get defaultBranch => _$this._defaultBranch;
  set defaultBranch(String? defaultBranch) =>
      _$this._defaultBranch = defaultBranch;

  String? _autoBranchPrefix;
  String? get autoBranchPrefix => _$this._autoBranchPrefix;
  set autoBranchPrefix(String? autoBranchPrefix) =>
      _$this._autoBranchPrefix = autoBranchPrefix;

  bool? _auditRequiredDefault;
  bool? get auditRequiredDefault => _$this._auditRequiredDefault;
  set auditRequiredDefault(bool? auditRequiredDefault) =>
      _$this._auditRequiredDefault = auditRequiredDefault;

  AgentHintsBuilder? _agentHints;
  AgentHintsBuilder get agentHints =>
      _$this._agentHints ??= AgentHintsBuilder();
  set agentHints(AgentHintsBuilder? agentHints) =>
      _$this._agentHints = agentHints;

  OrchestratorManifestBuilder() {
    OrchestratorManifest._defaults(this);
  }

  OrchestratorManifestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _dollarSchema = $v.dollarSchema;
      _schemaVersion = $v.schemaVersion;
      _projectId = $v.projectId;
      _projectName = $v.projectName;
      _orchestratorApi = $v.orchestratorApi;
      _defaultBranch = $v.defaultBranch;
      _autoBranchPrefix = $v.autoBranchPrefix;
      _auditRequiredDefault = $v.auditRequiredDefault;
      _agentHints = $v.agentHints?.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(OrchestratorManifest other) {
    _$v = other as _$OrchestratorManifest;
  }

  @override
  void update(void Function(OrchestratorManifestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  OrchestratorManifest build() => _build();

  _$OrchestratorManifest _build() {
    _$OrchestratorManifest _$result;
    try {
      _$result = _$v ??
          _$OrchestratorManifest._(
            dollarSchema: BuiltValueNullFieldError.checkNotNull(
                dollarSchema, r'OrchestratorManifest', 'dollarSchema'),
            schemaVersion: BuiltValueNullFieldError.checkNotNull(
                schemaVersion, r'OrchestratorManifest', 'schemaVersion'),
            projectId: BuiltValueNullFieldError.checkNotNull(
                projectId, r'OrchestratorManifest', 'projectId'),
            projectName: BuiltValueNullFieldError.checkNotNull(
                projectName, r'OrchestratorManifest', 'projectName'),
            orchestratorApi: BuiltValueNullFieldError.checkNotNull(
                orchestratorApi, r'OrchestratorManifest', 'orchestratorApi'),
            defaultBranch: BuiltValueNullFieldError.checkNotNull(
                defaultBranch, r'OrchestratorManifest', 'defaultBranch'),
            autoBranchPrefix: BuiltValueNullFieldError.checkNotNull(
                autoBranchPrefix, r'OrchestratorManifest', 'autoBranchPrefix'),
            auditRequiredDefault: BuiltValueNullFieldError.checkNotNull(
                auditRequiredDefault,
                r'OrchestratorManifest',
                'auditRequiredDefault'),
            agentHints: _agentHints?.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'agentHints';
        _agentHints?.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'OrchestratorManifest', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
