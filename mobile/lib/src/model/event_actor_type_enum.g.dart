// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'event_actor_type_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const EventActorTypeEnum _$owner = const EventActorTypeEnum._('owner');
const EventActorTypeEnum _$agent = const EventActorTypeEnum._('agent');
const EventActorTypeEnum _$system = const EventActorTypeEnum._('system');

EventActorTypeEnum _$valueOf(String name) {
  switch (name) {
    case 'owner':
      return _$owner;
    case 'agent':
      return _$agent;
    case 'system':
      return _$system;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<EventActorTypeEnum> _$values =
    BuiltSet<EventActorTypeEnum>(const <EventActorTypeEnum>[
  _$owner,
  _$agent,
  _$system,
]);

class _$EventActorTypeEnumMeta {
  const _$EventActorTypeEnumMeta();
  EventActorTypeEnum get owner => _$owner;
  EventActorTypeEnum get agent => _$agent;
  EventActorTypeEnum get system => _$system;
  EventActorTypeEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<EventActorTypeEnum> get values => _$values;
}

mixin _$EventActorTypeEnumMixin {
  // ignore: non_constant_identifier_names
  _$EventActorTypeEnumMeta get EventActorTypeEnum =>
      const _$EventActorTypeEnumMeta();
}

Serializer<EventActorTypeEnum> _$eventActorTypeEnumSerializer =
    _$EventActorTypeEnumSerializer();

class _$EventActorTypeEnumSerializer
    implements PrimitiveSerializer<EventActorTypeEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'owner': 'owner',
    'agent': 'agent',
    'system': 'system',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'owner': 'owner',
    'agent': 'agent',
    'system': 'system',
  };

  @override
  final Iterable<Type> types = const <Type>[EventActorTypeEnum];
  @override
  final String wireName = 'EventActorTypeEnum';

  @override
  Object serialize(Serializers serializers, EventActorTypeEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  EventActorTypeEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      EventActorTypeEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
