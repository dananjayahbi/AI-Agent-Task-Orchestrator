// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'transport_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const TransportEnum _$stdio = const TransportEnum._('stdio');
const TransportEnum _$http = const TransportEnum._('http');

TransportEnum _$valueOf(String name) {
  switch (name) {
    case 'stdio':
      return _$stdio;
    case 'http':
      return _$http;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<TransportEnum> _$values =
    BuiltSet<TransportEnum>(const <TransportEnum>[
  _$stdio,
  _$http,
]);

class _$TransportEnumMeta {
  const _$TransportEnumMeta();
  TransportEnum get stdio => _$stdio;
  TransportEnum get http => _$http;
  TransportEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<TransportEnum> get values => _$values;
}

mixin _$TransportEnumMixin {
  // ignore: non_constant_identifier_names
  _$TransportEnumMeta get TransportEnum => const _$TransportEnumMeta();
}

Serializer<TransportEnum> _$transportEnumSerializer =
    _$TransportEnumSerializer();

class _$TransportEnumSerializer implements PrimitiveSerializer<TransportEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'stdio': 'stdio',
    'http': 'http',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'stdio': 'stdio',
    'http': 'http',
  };

  @override
  final Iterable<Type> types = const <Type>[TransportEnum];
  @override
  final String wireName = 'TransportEnum';

  @override
  Object serialize(Serializers serializers, TransportEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  TransportEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      TransportEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
