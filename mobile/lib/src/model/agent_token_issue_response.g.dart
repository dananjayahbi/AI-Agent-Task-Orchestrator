// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agent_token_issue_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AgentTokenIssueResponse extends AgentTokenIssueResponse {
  @override
  final int id;
  @override
  final KindEnum kind;
  @override
  final String? projectId;
  @override
  final JsonObject? scopes;
  @override
  final DateTime? expiresAt;
  @override
  final String token;

  factory _$AgentTokenIssueResponse(
          [void Function(AgentTokenIssueResponseBuilder)? updates]) =>
      (AgentTokenIssueResponseBuilder()..update(updates))._build();

  _$AgentTokenIssueResponse._(
      {required this.id,
      required this.kind,
      this.projectId,
      this.scopes,
      this.expiresAt,
      required this.token})
      : super._();
  @override
  AgentTokenIssueResponse rebuild(
          void Function(AgentTokenIssueResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AgentTokenIssueResponseBuilder toBuilder() =>
      AgentTokenIssueResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AgentTokenIssueResponse &&
        id == other.id &&
        kind == other.kind &&
        projectId == other.projectId &&
        scopes == other.scopes &&
        expiresAt == other.expiresAt &&
        token == other.token;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, kind.hashCode);
    _$hash = $jc(_$hash, projectId.hashCode);
    _$hash = $jc(_$hash, scopes.hashCode);
    _$hash = $jc(_$hash, expiresAt.hashCode);
    _$hash = $jc(_$hash, token.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AgentTokenIssueResponse')
          ..add('id', id)
          ..add('kind', kind)
          ..add('projectId', projectId)
          ..add('scopes', scopes)
          ..add('expiresAt', expiresAt)
          ..add('token', token))
        .toString();
  }
}

class AgentTokenIssueResponseBuilder
    implements
        Builder<AgentTokenIssueResponse, AgentTokenIssueResponseBuilder> {
  _$AgentTokenIssueResponse? _$v;

  int? _id;
  int? get id => _$this._id;
  set id(int? id) => _$this._id = id;

  KindEnum? _kind;
  KindEnum? get kind => _$this._kind;
  set kind(KindEnum? kind) => _$this._kind = kind;

  String? _projectId;
  String? get projectId => _$this._projectId;
  set projectId(String? projectId) => _$this._projectId = projectId;

  JsonObject? _scopes;
  JsonObject? get scopes => _$this._scopes;
  set scopes(JsonObject? scopes) => _$this._scopes = scopes;

  DateTime? _expiresAt;
  DateTime? get expiresAt => _$this._expiresAt;
  set expiresAt(DateTime? expiresAt) => _$this._expiresAt = expiresAt;

  String? _token;
  String? get token => _$this._token;
  set token(String? token) => _$this._token = token;

  AgentTokenIssueResponseBuilder() {
    AgentTokenIssueResponse._defaults(this);
  }

  AgentTokenIssueResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _kind = $v.kind;
      _projectId = $v.projectId;
      _scopes = $v.scopes;
      _expiresAt = $v.expiresAt;
      _token = $v.token;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AgentTokenIssueResponse other) {
    _$v = other as _$AgentTokenIssueResponse;
  }

  @override
  void update(void Function(AgentTokenIssueResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AgentTokenIssueResponse build() => _build();

  _$AgentTokenIssueResponse _build() {
    final _$result = _$v ??
        _$AgentTokenIssueResponse._(
          id: BuiltValueNullFieldError.checkNotNull(
              id, r'AgentTokenIssueResponse', 'id'),
          kind: BuiltValueNullFieldError.checkNotNull(
              kind, r'AgentTokenIssueResponse', 'kind'),
          projectId: projectId,
          scopes: scopes,
          expiresAt: expiresAt,
          token: BuiltValueNullFieldError.checkNotNull(
              token, r'AgentTokenIssueResponse', 'token'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
