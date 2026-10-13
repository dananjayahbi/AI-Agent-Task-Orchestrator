// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'verdict_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const VerdictEnum _$pass = const VerdictEnum._('pass');
const VerdictEnum _$flagRisk = const VerdictEnum._('flagRisk');
const VerdictEnum _$fail = const VerdictEnum._('fail');

VerdictEnum _$valueOf(String name) {
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

final BuiltSet<VerdictEnum> _$values =
    BuiltSet<VerdictEnum>(const <VerdictEnum>[
  _$pass,
  _$flagRisk,
  _$fail,
]);

class _$VerdictEnumMeta {
  const _$VerdictEnumMeta();
  VerdictEnum get pass => _$pass;
  VerdictEnum get flagRisk => _$flagRisk;
  VerdictEnum get fail => _$fail;
  VerdictEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<VerdictEnum> get values => _$values;
}

mixin _$VerdictEnumMixin {
  // ignore: non_constant_identifier_names
  _$VerdictEnumMeta get VerdictEnum => const _$VerdictEnumMeta();
}

Serializer<VerdictEnum> _$verdictEnumSerializer = _$VerdictEnumSerializer();

class _$VerdictEnumSerializer implements PrimitiveSerializer<VerdictEnum> {
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
  final Iterable<Type> types = const <Type>[VerdictEnum];
  @override
  final String wireName = 'VerdictEnum';

  @override
  Object serialize(Serializers serializers, VerdictEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  VerdictEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      VerdictEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
