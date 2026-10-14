// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'decision_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const DecisionEnum _$approve = const DecisionEnum._('approve');
const DecisionEnum _$requestChanges = const DecisionEnum._('requestChanges');
const DecisionEnum _$reassign = const DecisionEnum._('reassign');

DecisionEnum _$valueOf(String name) {
  switch (name) {
    case 'approve':
      return _$approve;
    case 'requestChanges':
      return _$requestChanges;
    case 'reassign':
      return _$reassign;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<DecisionEnum> _$values =
    BuiltSet<DecisionEnum>(const <DecisionEnum>[
  _$approve,
  _$requestChanges,
  _$reassign,
]);

class _$DecisionEnumMeta {
  const _$DecisionEnumMeta();
  DecisionEnum get approve => _$approve;
  DecisionEnum get requestChanges => _$requestChanges;
  DecisionEnum get reassign => _$reassign;
  DecisionEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<DecisionEnum> get values => _$values;
}

mixin _$DecisionEnumMixin {
  // ignore: non_constant_identifier_names
  _$DecisionEnumMeta get DecisionEnum => const _$DecisionEnumMeta();
}

Serializer<DecisionEnum> _$decisionEnumSerializer = _$DecisionEnumSerializer();

class _$DecisionEnumSerializer implements PrimitiveSerializer<DecisionEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'approve': 'approve',
    'requestChanges': 'request_changes',
    'reassign': 'reassign',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'approve': 'approve',
    'request_changes': 'requestChanges',
    'reassign': 'reassign',
  };

  @override
  final Iterable<Type> types = const <Type>[DecisionEnum];
  @override
  final String wireName = 'DecisionEnum';

  @override
  Object serialize(Serializers serializers, DecisionEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  DecisionEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      DecisionEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
