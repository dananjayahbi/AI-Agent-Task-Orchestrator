// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'token_summary.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$TokenSummary extends TokenSummary {
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
  final DateTime? revokedAt;
  @override
  final DateTime? lastUsedAt;

  factory _$TokenSummary([void Function(TokenSummaryBuilder)? updates]) =>
      (TokenSummaryBuilder()..update(updates))._build();

  _$TokenSummary._(
      {required this.id,
      required this.kind,
      this.projectId,
      this.scopes,
      this.expiresAt,
      this.revokedAt,
      this.lastUsedAt})
      : super._();
  @override
  TokenSummary rebuild(void Function(TokenSummaryBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  TokenSummaryBuilder toBuilder() => TokenSummaryBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is TokenSummary &&
        id == other.id &&
        kind == other.kind &&
        projectId == other.projectId &&
        scopes == other.scopes &&
        expiresAt == other.expiresAt &&
        revokedAt == other.revokedAt &&
        lastUsedAt == other.lastUsedAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, kind.hashCode);
    _$hash = $jc(_$hash, projectId.hashCode);
    _$hash = $jc(_$hash, scopes.hashCode);
    _$hash = $jc(_$hash, expiresAt.hashCode);
    _$hash = $jc(_$hash, revokedAt.hashCode);
    _$hash = $jc(_$hash, lastUsedAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'TokenSummary')
          ..add('id', id)
          ..add('kind', kind)
          ..add('projectId', projectId)
          ..add('scopes', scopes)
          ..add('expiresAt', expiresAt)
          ..add('revokedAt', revokedAt)
          ..add('lastUsedAt', lastUsedAt))
        .toString();
  }
}

class TokenSummaryBuilder
    implements Builder<TokenSummary, TokenSummaryBuilder> {
  _$TokenSummary? _$v;

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

  DateTime? _revokedAt;
  DateTime? get revokedAt => _$this._revokedAt;
  set revokedAt(DateTime? revokedAt) => _$this._revokedAt = revokedAt;

  DateTime? _lastUsedAt;
  DateTime? get lastUsedAt => _$this._lastUsedAt;
  set lastUsedAt(DateTime? lastUsedAt) => _$this._lastUsedAt = lastUsedAt;

  TokenSummaryBuilder() {
    TokenSummary._defaults(this);
  }

  TokenSummaryBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _kind = $v.kind;
      _projectId = $v.projectId;
      _scopes = $v.scopes;
      _expiresAt = $v.expiresAt;
      _revokedAt = $v.revokedAt;
      _lastUsedAt = $v.lastUsedAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(TokenSummary other) {
    _$v = other as _$TokenSummary;
  }

  @override
  void update(void Function(TokenSummaryBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  TokenSummary build() => _build();

  _$TokenSummary _build() {
    final _$result = _$v ??
        _$TokenSummary._(
          id: BuiltValueNullFieldError.checkNotNull(id, r'TokenSummary', 'id'),
          kind: BuiltValueNullFieldError.checkNotNull(
              kind, r'TokenSummary', 'kind'),
          projectId: projectId,
          scopes: scopes,
          expiresAt: expiresAt,
          revokedAt: revokedAt,
          lastUsedAt: lastUsedAt,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
