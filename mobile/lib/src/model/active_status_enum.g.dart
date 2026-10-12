// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'active_status_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const ActiveStatusEnum _$active = const ActiveStatusEnum._('active');
const ActiveStatusEnum _$paused = const ActiveStatusEnum._('paused');
const ActiveStatusEnum _$archived = const ActiveStatusEnum._('archived');

ActiveStatusEnum _$valueOf(String name) {
  switch (name) {
    case 'active':
      return _$active;
    case 'paused':
      return _$paused;
    case 'archived':
      return _$archived;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<ActiveStatusEnum> _$values =
    BuiltSet<ActiveStatusEnum>(const <ActiveStatusEnum>[
  _$active,
  _$paused,
  _$archived,
]);

class _$ActiveStatusEnumMeta {
  const _$ActiveStatusEnumMeta();
  ActiveStatusEnum get active => _$active;
  ActiveStatusEnum get paused => _$paused;
  ActiveStatusEnum get archived => _$archived;
  ActiveStatusEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<ActiveStatusEnum> get values => _$values;
}

mixin _$ActiveStatusEnumMixin {
  // ignore: non_constant_identifier_names
  _$ActiveStatusEnumMeta get ActiveStatusEnum => const _$ActiveStatusEnumMeta();
}

Serializer<ActiveStatusEnum> _$activeStatusEnumSerializer =
    _$ActiveStatusEnumSerializer();

class _$ActiveStatusEnumSerializer
    implements PrimitiveSerializer<ActiveStatusEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'active': 'active',
    'paused': 'paused',
    'archived': 'archived',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'active': 'active',
    'paused': 'paused',
    'archived': 'archived',
  };

  @override
  final Iterable<Type> types = const <Type>[ActiveStatusEnum];
  @override
  final String wireName = 'ActiveStatusEnum';

  @override
  Object serialize(Serializers serializers, ActiveStatusEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  ActiveStatusEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      ActiveStatusEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
