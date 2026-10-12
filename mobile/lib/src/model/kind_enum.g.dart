// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'kind_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const KindEnum _$ownerSession = const KindEnum._('ownerSession');
const KindEnum _$agent = const KindEnum._('agent');
const KindEnum _$device = const KindEnum._('device');

KindEnum _$valueOf(String name) {
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

final BuiltSet<KindEnum> _$values = BuiltSet<KindEnum>(const <KindEnum>[
  _$ownerSession,
  _$agent,
  _$device,
]);

class _$KindEnumMeta {
  const _$KindEnumMeta();
  KindEnum get ownerSession => _$ownerSession;
  KindEnum get agent => _$agent;
  KindEnum get device => _$device;
  KindEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<KindEnum> get values => _$values;
}

mixin _$KindEnumMixin {
  // ignore: non_constant_identifier_names
  _$KindEnumMeta get KindEnum => const _$KindEnumMeta();
}

Serializer<KindEnum> _$kindEnumSerializer = _$KindEnumSerializer();

class _$KindEnumSerializer implements PrimitiveSerializer<KindEnum> {
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
  final Iterable<Type> types = const <Type>[KindEnum];
  @override
  final String wireName = 'KindEnum';

  @override
  Object serialize(Serializers serializers, KindEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  KindEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      KindEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
