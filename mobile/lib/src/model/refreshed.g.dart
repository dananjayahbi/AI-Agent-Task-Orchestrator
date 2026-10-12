// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'refreshed.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$Refreshed extends Refreshed {
  @override
  final DateTime expiresAt;

  factory _$Refreshed([void Function(RefreshedBuilder)? updates]) =>
      (RefreshedBuilder()..update(updates))._build();

  _$Refreshed._({required this.expiresAt}) : super._();
  @override
  Refreshed rebuild(void Function(RefreshedBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  RefreshedBuilder toBuilder() => RefreshedBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is Refreshed && expiresAt == other.expiresAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, expiresAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'Refreshed')
          ..add('expiresAt', expiresAt))
        .toString();
  }
}

class RefreshedBuilder implements Builder<Refreshed, RefreshedBuilder> {
  _$Refreshed? _$v;

  DateTime? _expiresAt;
  DateTime? get expiresAt => _$this._expiresAt;
  set expiresAt(DateTime? expiresAt) => _$this._expiresAt = expiresAt;

  RefreshedBuilder() {
    Refreshed._defaults(this);
  }

  RefreshedBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _expiresAt = $v.expiresAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(Refreshed other) {
    _$v = other as _$Refreshed;
  }

  @override
  void update(void Function(RefreshedBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  Refreshed build() => _build();

  _$Refreshed _build() {
    final _$result = _$v ??
        _$Refreshed._(
          expiresAt: BuiltValueNullFieldError.checkNotNull(
              expiresAt, r'Refreshed', 'expiresAt'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
