// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'revoked.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$Revoked extends Revoked {
  @override
  final DateTime revokedAt;

  factory _$Revoked([void Function(RevokedBuilder)? updates]) =>
      (RevokedBuilder()..update(updates))._build();

  _$Revoked._({required this.revokedAt}) : super._();
  @override
  Revoked rebuild(void Function(RevokedBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  RevokedBuilder toBuilder() => RevokedBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is Revoked && revokedAt == other.revokedAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, revokedAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'Revoked')
          ..add('revokedAt', revokedAt))
        .toString();
  }
}

class RevokedBuilder implements Builder<Revoked, RevokedBuilder> {
  _$Revoked? _$v;

  DateTime? _revokedAt;
  DateTime? get revokedAt => _$this._revokedAt;
  set revokedAt(DateTime? revokedAt) => _$this._revokedAt = revokedAt;

  RevokedBuilder() {
    Revoked._defaults(this);
  }

  RevokedBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _revokedAt = $v.revokedAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(Revoked other) {
    _$v = other as _$Revoked;
  }

  @override
  void update(void Function(RevokedBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  Revoked build() => _build();

  _$Revoked _build() {
    final _$result = _$v ??
        _$Revoked._(
          revokedAt: BuiltValueNullFieldError.checkNotNull(
              revokedAt, r'Revoked', 'revokedAt'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
