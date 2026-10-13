// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'policy_decision_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const PolicyDecisionEnum _$approve = const PolicyDecisionEnum._('approve');
const PolicyDecisionEnum _$escalate = const PolicyDecisionEnum._('escalate');

PolicyDecisionEnum _$valueOf(String name) {
  switch (name) {
    case 'approve':
      return _$approve;
    case 'escalate':
      return _$escalate;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<PolicyDecisionEnum> _$values =
    BuiltSet<PolicyDecisionEnum>(const <PolicyDecisionEnum>[
  _$approve,
  _$escalate,
]);

class _$PolicyDecisionEnumMeta {
  const _$PolicyDecisionEnumMeta();
  PolicyDecisionEnum get approve => _$approve;
  PolicyDecisionEnum get escalate => _$escalate;
  PolicyDecisionEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<PolicyDecisionEnum> get values => _$values;
}

mixin _$PolicyDecisionEnumMixin {
  // ignore: non_constant_identifier_names
  _$PolicyDecisionEnumMeta get PolicyDecisionEnum =>
      const _$PolicyDecisionEnumMeta();
}

Serializer<PolicyDecisionEnum> _$policyDecisionEnumSerializer =
    _$PolicyDecisionEnumSerializer();

class _$PolicyDecisionEnumSerializer
    implements PrimitiveSerializer<PolicyDecisionEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'approve': 'approve',
    'escalate': 'escalate',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'approve': 'approve',
    'escalate': 'escalate',
  };

  @override
  final Iterable<Type> types = const <Type>[PolicyDecisionEnum];
  @override
  final String wireName = 'PolicyDecisionEnum';

  @override
  Object serialize(Serializers serializers, PolicyDecisionEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  PolicyDecisionEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      PolicyDecisionEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
