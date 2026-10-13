// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'proposed_verdict_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const ProposedVerdictEnum _$pass = const ProposedVerdictEnum._('pass');
const ProposedVerdictEnum _$flagRisk = const ProposedVerdictEnum._('flagRisk');
const ProposedVerdictEnum _$fail = const ProposedVerdictEnum._('fail');

ProposedVerdictEnum _$valueOf(String name) {
  switch (name) {
    case 'pass':
      return _$pass;
    case 'flagRisk':
      return _$flagRisk;
    case 'fail':
      return _$fail;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<ProposedVerdictEnum> _$values =
    BuiltSet<ProposedVerdictEnum>(const <ProposedVerdictEnum>[
  _$pass,
  _$flagRisk,
  _$fail,
]);

class _$ProposedVerdictEnumMeta {
  const _$ProposedVerdictEnumMeta();
  ProposedVerdictEnum get pass => _$pass;
  ProposedVerdictEnum get flagRisk => _$flagRisk;
  ProposedVerdictEnum get fail => _$fail;
  ProposedVerdictEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<ProposedVerdictEnum> get values => _$values;
}

mixin _$ProposedVerdictEnumMixin {
  // ignore: non_constant_identifier_names
  _$ProposedVerdictEnumMeta get ProposedVerdictEnum =>
      const _$ProposedVerdictEnumMeta();
}

Serializer<ProposedVerdictEnum> _$proposedVerdictEnumSerializer =
    _$ProposedVerdictEnumSerializer();

class _$ProposedVerdictEnumSerializer
    implements PrimitiveSerializer<ProposedVerdictEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'pass': 'pass',
    'flagRisk': 'flag_risk',
    'fail': 'fail',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'pass': 'pass',
    'flag_risk': 'flagRisk',
    'fail': 'fail',
  };

  @override
  final Iterable<Type> types = const <Type>[ProposedVerdictEnum];
  @override
  final String wireName = 'ProposedVerdictEnum';

  @override
  Object serialize(Serializers serializers, ProposedVerdictEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  ProposedVerdictEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      ProposedVerdictEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
