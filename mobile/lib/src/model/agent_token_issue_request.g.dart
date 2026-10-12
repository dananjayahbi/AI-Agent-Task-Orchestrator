// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agent_token_issue_request.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AgentTokenIssueRequest extends AgentTokenIssueRequest {
  @override
  final String projectId;
  @override
  final BuiltList<String>? scopes;

  factory _$AgentTokenIssueRequest(
          [void Function(AgentTokenIssueRequestBuilder)? updates]) =>
      (AgentTokenIssueRequestBuilder()..update(updates))._build();

  _$AgentTokenIssueRequest._({required this.projectId, this.scopes})
      : super._();
  @override
  AgentTokenIssueRequest rebuild(
          void Function(AgentTokenIssueRequestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AgentTokenIssueRequestBuilder toBuilder() =>
      AgentTokenIssueRequestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AgentTokenIssueRequest &&
        projectId == other.projectId &&
        scopes == other.scopes;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, projectId.hashCode);
    _$hash = $jc(_$hash, scopes.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AgentTokenIssueRequest')
          ..add('projectId', projectId)
          ..add('scopes', scopes))
        .toString();
  }
}

class AgentTokenIssueRequestBuilder
    implements Builder<AgentTokenIssueRequest, AgentTokenIssueRequestBuilder> {
  _$AgentTokenIssueRequest? _$v;

  String? _projectId;
  String? get projectId => _$this._projectId;
  set projectId(String? projectId) => _$this._projectId = projectId;

  ListBuilder<String>? _scopes;
  ListBuilder<String> get scopes => _$this._scopes ??= ListBuilder<String>();
  set scopes(ListBuilder<String>? scopes) => _$this._scopes = scopes;

  AgentTokenIssueRequestBuilder() {
    AgentTokenIssueRequest._defaults(this);
  }

  AgentTokenIssueRequestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _projectId = $v.projectId;
      _scopes = $v.scopes?.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AgentTokenIssueRequest other) {
    _$v = other as _$AgentTokenIssueRequest;
  }

  @override
  void update(void Function(AgentTokenIssueRequestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AgentTokenIssueRequest build() => _build();

  _$AgentTokenIssueRequest _build() {
    _$AgentTokenIssueRequest _$result;
    try {
      _$result = _$v ??
          _$AgentTokenIssueRequest._(
            projectId: BuiltValueNullFieldError.checkNotNull(
                projectId, r'AgentTokenIssueRequest', 'projectId'),
            scopes: _scopes?.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'scopes';
        _scopes?.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'AgentTokenIssueRequest', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
