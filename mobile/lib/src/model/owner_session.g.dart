// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'owner_session.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$OwnerSession extends OwnerSession {
  @override
  final String token;
  @override
  final DateTime expiresAt;
  @override
  final UserSummary user;

  factory _$OwnerSession([void Function(OwnerSessionBuilder)? updates]) =>
      (OwnerSessionBuilder()..update(updates))._build();

  _$OwnerSession._(
      {required this.token, required this.expiresAt, required this.user})
      : super._();
  @override
  OwnerSession rebuild(void Function(OwnerSessionBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  OwnerSessionBuilder toBuilder() => OwnerSessionBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is OwnerSession &&
        token == other.token &&
        expiresAt == other.expiresAt &&
        user == other.user;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, token.hashCode);
    _$hash = $jc(_$hash, expiresAt.hashCode);
    _$hash = $jc(_$hash, user.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'OwnerSession')
          ..add('token', token)
          ..add('expiresAt', expiresAt)
          ..add('user', user))
        .toString();
  }
}

class OwnerSessionBuilder
    implements Builder<OwnerSession, OwnerSessionBuilder> {
  _$OwnerSession? _$v;

  String? _token;
  String? get token => _$this._token;
  set token(String? token) => _$this._token = token;

  DateTime? _expiresAt;
  DateTime? get expiresAt => _$this._expiresAt;
  set expiresAt(DateTime? expiresAt) => _$this._expiresAt = expiresAt;

  UserSummaryBuilder? _user;
  UserSummaryBuilder get user => _$this._user ??= UserSummaryBuilder();
  set user(UserSummaryBuilder? user) => _$this._user = user;

  OwnerSessionBuilder() {
    OwnerSession._defaults(this);
  }

  OwnerSessionBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _token = $v.token;
      _expiresAt = $v.expiresAt;
      _user = $v.user.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(OwnerSession other) {
    _$v = other as _$OwnerSession;
  }

  @override
  void update(void Function(OwnerSessionBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  OwnerSession build() => _build();

  _$OwnerSession _build() {
    _$OwnerSession _$result;
    try {
      _$result = _$v ??
          _$OwnerSession._(
            token: BuiltValueNullFieldError.checkNotNull(
                token, r'OwnerSession', 'token'),
            expiresAt: BuiltValueNullFieldError.checkNotNull(
                expiresAt, r'OwnerSession', 'expiresAt'),
            user: user.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'user';
        user.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'OwnerSession', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
