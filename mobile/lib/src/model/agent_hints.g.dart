// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agent_hints.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AgentHints extends AgentHints {
  @override
  final String? testCommandDefault;
  @override
  final bool? worktreeMode;

  factory _$AgentHints([void Function(AgentHintsBuilder)? updates]) =>
      (AgentHintsBuilder()..update(updates))._build();

  _$AgentHints._({this.testCommandDefault, this.worktreeMode}) : super._();
  @override
  AgentHints rebuild(void Function(AgentHintsBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AgentHintsBuilder toBuilder() => AgentHintsBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AgentHints &&
        testCommandDefault == other.testCommandDefault &&
        worktreeMode == other.worktreeMode;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, testCommandDefault.hashCode);
    _$hash = $jc(_$hash, worktreeMode.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AgentHints')
          ..add('testCommandDefault', testCommandDefault)
          ..add('worktreeMode', worktreeMode))
        .toString();
  }
}

class AgentHintsBuilder implements Builder<AgentHints, AgentHintsBuilder> {
  _$AgentHints? _$v;

  String? _testCommandDefault;
  String? get testCommandDefault => _$this._testCommandDefault;
  set testCommandDefault(String? testCommandDefault) =>
      _$this._testCommandDefault = testCommandDefault;

  bool? _worktreeMode;
  bool? get worktreeMode => _$this._worktreeMode;
  set worktreeMode(bool? worktreeMode) => _$this._worktreeMode = worktreeMode;

  AgentHintsBuilder() {
    AgentHints._defaults(this);
  }

  AgentHintsBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _testCommandDefault = $v.testCommandDefault;
      _worktreeMode = $v.worktreeMode;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AgentHints other) {
    _$v = other as _$AgentHints;
  }

  @override
  void update(void Function(AgentHintsBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AgentHints build() => _build();

  _$AgentHints _build() {
    final _$result = _$v ??
        _$AgentHints._(
          testCommandDefault: testCommandDefault,
          worktreeMode: worktreeMode,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
