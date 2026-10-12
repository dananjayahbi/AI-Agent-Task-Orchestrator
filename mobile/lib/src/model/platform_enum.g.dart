// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'platform_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const PlatformEnum _$ios = const PlatformEnum._('ios');
const PlatformEnum _$android = const PlatformEnum._('android');

PlatformEnum _$valueOf(String name) {
  switch (name) {
    case 'ios':
      return _$ios;
    case 'android':
      return _$android;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<PlatformEnum> _$values =
    BuiltSet<PlatformEnum>(const <PlatformEnum>[
  _$ios,
  _$android,
]);

class _$PlatformEnumMeta {
  const _$PlatformEnumMeta();
  PlatformEnum get ios => _$ios;
  PlatformEnum get android => _$android;
  PlatformEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<PlatformEnum> get values => _$values;
}

mixin _$PlatformEnumMixin {
  // ignore: non_constant_identifier_names
  _$PlatformEnumMeta get PlatformEnum => const _$PlatformEnumMeta();
}

Serializer<PlatformEnum> _$platformEnumSerializer = _$PlatformEnumSerializer();

class _$PlatformEnumSerializer implements PrimitiveSerializer<PlatformEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'ios': 'ios',
    'android': 'android',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'ios': 'ios',
    'android': 'android',
  };

  @override
  final Iterable<Type> types = const <Type>[PlatformEnum];
  @override
  final String wireName = 'PlatformEnum';

  @override
  Object serialize(Serializers serializers, PlatformEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  PlatformEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      PlatformEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
