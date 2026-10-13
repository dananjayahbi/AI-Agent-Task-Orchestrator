// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'policy_preset_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const PolicyPresetEnum _$django = const PolicyPresetEnum._('django');
const PolicyPresetEnum _$nextjs = const PolicyPresetEnum._('nextjs');
const PolicyPresetEnum _$flutter = const PolicyPresetEnum._('flutter');

PolicyPresetEnum _$valueOf(String name) {
  switch (name) {
    case 'django':
      return _$django;
    case 'nextjs':
      return _$nextjs;
    case 'flutter':
      return _$flutter;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<PolicyPresetEnum> _$values =
    BuiltSet<PolicyPresetEnum>(const <PolicyPresetEnum>[
  _$django,
  _$nextjs,
  _$flutter,
]);

class _$PolicyPresetEnumMeta {
  const _$PolicyPresetEnumMeta();
  PolicyPresetEnum get django => _$django;
  PolicyPresetEnum get nextjs => _$nextjs;
  PolicyPresetEnum get flutter => _$flutter;
  PolicyPresetEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<PolicyPresetEnum> get values => _$values;
}

mixin _$PolicyPresetEnumMixin {
  // ignore: non_constant_identifier_names
  _$PolicyPresetEnumMeta get PolicyPresetEnum => const _$PolicyPresetEnumMeta();
}

Serializer<PolicyPresetEnum> _$policyPresetEnumSerializer =
    _$PolicyPresetEnumSerializer();

class _$PolicyPresetEnumSerializer
    implements PrimitiveSerializer<PolicyPresetEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'django': 'django',
    'nextjs': 'nextjs',
    'flutter': 'flutter',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'django': 'django',
    'nextjs': 'nextjs',
    'flutter': 'flutter',
  };

  @override
  final Iterable<Type> types = const <Type>[PolicyPresetEnum];
  @override
  final String wireName = 'PolicyPresetEnum';

  @override
  Object serialize(Serializers serializers, PolicyPresetEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  PolicyPresetEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      PolicyPresetEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
