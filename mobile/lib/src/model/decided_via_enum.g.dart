// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'decided_via_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const DecidedViaEnum _$web = const DecidedViaEnum._('web');
const DecidedViaEnum _$mobile = const DecidedViaEnum._('mobile');

DecidedViaEnum _$valueOf(String name) {
  switch (name) {
    case 'web':
      return _$web;
    case 'mobile':
      return _$mobile;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<DecidedViaEnum> _$values =
    BuiltSet<DecidedViaEnum>(const <DecidedViaEnum>[
  _$web,
  _$mobile,
]);

class _$DecidedViaEnumMeta {
  const _$DecidedViaEnumMeta();
  DecidedViaEnum get web => _$web;
  DecidedViaEnum get mobile => _$mobile;
  DecidedViaEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<DecidedViaEnum> get values => _$values;
}

mixin _$DecidedViaEnumMixin {
  // ignore: non_constant_identifier_names
  _$DecidedViaEnumMeta get DecidedViaEnum => const _$DecidedViaEnumMeta();
}

Serializer<DecidedViaEnum> _$decidedViaEnumSerializer =
    _$DecidedViaEnumSerializer();

class _$DecidedViaEnumSerializer
    implements PrimitiveSerializer<DecidedViaEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'web': 'web',
    'mobile': 'mobile',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'web': 'web',
    'mobile': 'mobile',
  };

  @override
  final Iterable<Type> types = const <Type>[DecidedViaEnum];
  @override
  final String wireName = 'DecidedViaEnum';

  @override
  Object serialize(Serializers serializers, DecidedViaEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  DecidedViaEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      DecidedViaEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
