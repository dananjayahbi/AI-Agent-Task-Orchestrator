// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'role_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const RoleEnum _$coder = const RoleEnum._('coder');
const RoleEnum _$auditor = const RoleEnum._('auditor');

RoleEnum _$valueOf(String name) {
  switch (name) {
    case 'coder':
      return _$coder;
    case 'auditor':
      return _$auditor;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<RoleEnum> _$values = BuiltSet<RoleEnum>(const <RoleEnum>[
  _$coder,
  _$auditor,
]);

class _$RoleEnumMeta {
  const _$RoleEnumMeta();
  RoleEnum get coder => _$coder;
  RoleEnum get auditor => _$auditor;
  RoleEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<RoleEnum> get values => _$values;
}

mixin _$RoleEnumMixin {
  // ignore: non_constant_identifier_names
  _$RoleEnumMeta get RoleEnum => const _$RoleEnumMeta();
}

Serializer<RoleEnum> _$roleEnumSerializer = _$RoleEnumSerializer();

class _$RoleEnumSerializer implements PrimitiveSerializer<RoleEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'coder': 'coder',
    'auditor': 'auditor',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'coder': 'coder',
    'auditor': 'auditor',
  };

  @override
  final Iterable<Type> types = const <Type>[RoleEnum];
  @override
  final String wireName = 'RoleEnum';

  @override
  Object serialize(Serializers serializers, RoleEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  RoleEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      RoleEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
