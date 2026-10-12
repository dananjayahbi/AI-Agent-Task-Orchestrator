// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'priority_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const PriorityEnum _$urgent = const PriorityEnum._('urgent');
const PriorityEnum _$high = const PriorityEnum._('high');
const PriorityEnum _$medium = const PriorityEnum._('medium');
const PriorityEnum _$low = const PriorityEnum._('low');

PriorityEnum _$valueOf(String name) {
  switch (name) {
    case 'urgent':
      return _$urgent;
    case 'high':
      return _$high;
    case 'medium':
      return _$medium;
    case 'low':
      return _$low;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<PriorityEnum> _$values =
    BuiltSet<PriorityEnum>(const <PriorityEnum>[
  _$urgent,
  _$high,
  _$medium,
  _$low,
]);

class _$PriorityEnumMeta {
  const _$PriorityEnumMeta();
  PriorityEnum get urgent => _$urgent;
  PriorityEnum get high => _$high;
  PriorityEnum get medium => _$medium;
  PriorityEnum get low => _$low;
  PriorityEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<PriorityEnum> get values => _$values;
}

mixin _$PriorityEnumMixin {
  // ignore: non_constant_identifier_names
  _$PriorityEnumMeta get PriorityEnum => const _$PriorityEnumMeta();
}

Serializer<PriorityEnum> _$priorityEnumSerializer = _$PriorityEnumSerializer();

class _$PriorityEnumSerializer implements PrimitiveSerializer<PriorityEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'urgent': 'urgent',
    'high': 'high',
    'medium': 'medium',
    'low': 'low',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'urgent': 'urgent',
    'high': 'high',
    'medium': 'medium',
    'low': 'low',
  };

  @override
  final Iterable<Type> types = const <Type>[PriorityEnum];
  @override
  final String wireName = 'PriorityEnum';

  @override
  Object serialize(Serializers serializers, PriorityEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  PriorityEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      PriorityEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
