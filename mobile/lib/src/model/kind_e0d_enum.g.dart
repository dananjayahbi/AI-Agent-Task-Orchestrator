// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'kind_e0d_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const KindE0dEnum _$ownerSession = const KindE0dEnum._('ownerSession');
const KindE0dEnum _$agent = const KindE0dEnum._('agent');
const KindE0dEnum _$device = const KindE0dEnum._('device');

KindE0dEnum _$valueOf(String name) {
  switch (name) {
    case 'ownerSession':
      return _$ownerSession;
    case 'agent':
      return _$agent;
    case 'device':
      return _$device;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<KindE0dEnum> _$values =
    BuiltSet<KindE0dEnum>(const <KindE0dEnum>[
  _$ownerSession,
  _$agent,
  _$device,
]);

class _$KindE0dEnumMeta {
  const _$KindE0dEnumMeta();
  KindE0dEnum get ownerSession => _$ownerSession;
  KindE0dEnum get agent => _$agent;
  KindE0dEnum get device => _$device;
  KindE0dEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<KindE0dEnum> get values => _$values;
}

mixin _$KindE0dEnumMixin {
  // ignore: non_constant_identifier_names
  _$KindE0dEnumMeta get KindE0dEnum => const _$KindE0dEnumMeta();
}

Serializer<KindE0dEnum> _$kindE0dEnumSerializer = _$KindE0dEnumSerializer();

class _$KindE0dEnumSerializer implements PrimitiveSerializer<KindE0dEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'ownerSession': 'owner_session',
    'agent': 'agent',
    'device': 'device',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'owner_session': 'ownerSession',
    'agent': 'agent',
    'device': 'device',
  };

  @override
  final Iterable<Type> types = const <Type>[KindE0dEnum];
  @override
  final String wireName = 'KindE0dEnum';

  @override
  Object serialize(Serializers serializers, KindE0dEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  KindE0dEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      KindE0dEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
