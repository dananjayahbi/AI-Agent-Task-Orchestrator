// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'rules_block.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$RulesBlock extends RulesBlock {
  @override
  final BuiltList<String> standardRules;
  @override
  final String projectRules;

  factory _$RulesBlock([void Function(RulesBlockBuilder)? updates]) =>
      (RulesBlockBuilder()..update(updates))._build();

  _$RulesBlock._({required this.standardRules, required this.projectRules})
      : super._();
  @override
  RulesBlock rebuild(void Function(RulesBlockBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  RulesBlockBuilder toBuilder() => RulesBlockBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is RulesBlock &&
        standardRules == other.standardRules &&
        projectRules == other.projectRules;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, standardRules.hashCode);
    _$hash = $jc(_$hash, projectRules.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'RulesBlock')
          ..add('standardRules', standardRules)
          ..add('projectRules', projectRules))
        .toString();
  }
}

class RulesBlockBuilder implements Builder<RulesBlock, RulesBlockBuilder> {
  _$RulesBlock? _$v;

  ListBuilder<String>? _standardRules;
  ListBuilder<String> get standardRules =>
      _$this._standardRules ??= ListBuilder<String>();
  set standardRules(ListBuilder<String>? standardRules) =>
      _$this._standardRules = standardRules;

  String? _projectRules;
  String? get projectRules => _$this._projectRules;
  set projectRules(String? projectRules) => _$this._projectRules = projectRules;

  RulesBlockBuilder() {
    RulesBlock._defaults(this);
  }

  RulesBlockBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _standardRules = $v.standardRules.toBuilder();
      _projectRules = $v.projectRules;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(RulesBlock other) {
    _$v = other as _$RulesBlock;
  }

  @override
  void update(void Function(RulesBlockBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  RulesBlock build() => _build();

  _$RulesBlock _build() {
    _$RulesBlock _$result;
    try {
      _$result = _$v ??
          _$RulesBlock._(
            standardRules: standardRules.build(),
            projectRules: BuiltValueNullFieldError.checkNotNull(
                projectRules, r'RulesBlock', 'projectRules'),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'standardRules';
        standardRules.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'RulesBlock', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
