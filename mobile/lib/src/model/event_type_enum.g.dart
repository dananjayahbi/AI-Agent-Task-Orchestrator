// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'event_type_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const EventTypeEnum _$inHumanReview = const EventTypeEnum._('inHumanReview');
const EventTypeEnum _$mergeFailure = const EventTypeEnum._('mergeFailure');
const EventTypeEnum _$retryExhaustion =
    const EventTypeEnum._('retryExhaustion');
const EventTypeEnum _$completionDigest =
    const EventTypeEnum._('completionDigest');

EventTypeEnum _$valueOf(String name) {
  switch (name) {
    case 'inHumanReview':
      return _$inHumanReview;
    case 'mergeFailure':
      return _$mergeFailure;
    case 'retryExhaustion':
      return _$retryExhaustion;
    case 'completionDigest':
      return _$completionDigest;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<EventTypeEnum> _$values =
    BuiltSet<EventTypeEnum>(const <EventTypeEnum>[
  _$inHumanReview,
  _$mergeFailure,
  _$retryExhaustion,
  _$completionDigest,
]);

class _$EventTypeEnumMeta {
  const _$EventTypeEnumMeta();
  EventTypeEnum get inHumanReview => _$inHumanReview;
  EventTypeEnum get mergeFailure => _$mergeFailure;
  EventTypeEnum get retryExhaustion => _$retryExhaustion;
  EventTypeEnum get completionDigest => _$completionDigest;
  EventTypeEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<EventTypeEnum> get values => _$values;
}

mixin _$EventTypeEnumMixin {
  // ignore: non_constant_identifier_names
  _$EventTypeEnumMeta get EventTypeEnum => const _$EventTypeEnumMeta();
}

Serializer<EventTypeEnum> _$eventTypeEnumSerializer =
    _$EventTypeEnumSerializer();

class _$EventTypeEnumSerializer implements PrimitiveSerializer<EventTypeEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'inHumanReview': 'in_human_review',
    'mergeFailure': 'merge_failure',
    'retryExhaustion': 'retry_exhaustion',
    'completionDigest': 'completion_digest',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'in_human_review': 'inHumanReview',
    'merge_failure': 'mergeFailure',
    'retry_exhaustion': 'retryExhaustion',
    'completion_digest': 'completionDigest',
  };

  @override
  final Iterable<Type> types = const <Type>[EventTypeEnum];
  @override
  final String wireName = 'EventTypeEnum';

  @override
  Object serialize(Serializers serializers, EventTypeEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  EventTypeEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      EventTypeEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
