// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'capability_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const CapabilityEnum _$vision = const CapabilityEnum._('vision');
const CapabilityEnum _$textOnly = const CapabilityEnum._('textOnly');
const CapabilityEnum _$unknown = const CapabilityEnum._('unknown');

CapabilityEnum _$valueOf(String name) {
  switch (name) {
    case 'vision':
      return _$vision;
    case 'textOnly':
      return _$textOnly;
    case 'unknown':
      return _$unknown;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<CapabilityEnum> _$values =
    BuiltSet<CapabilityEnum>(const <CapabilityEnum>[
  _$vision,
  _$textOnly,
  _$unknown,
]);

class _$CapabilityEnumMeta {
  const _$CapabilityEnumMeta();
  CapabilityEnum get vision => _$vision;
  CapabilityEnum get textOnly => _$textOnly;
  CapabilityEnum get unknown => _$unknown;
  CapabilityEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<CapabilityEnum> get values => _$values;
}

mixin _$CapabilityEnumMixin {
  // ignore: non_constant_identifier_names
  _$CapabilityEnumMeta get CapabilityEnum => const _$CapabilityEnumMeta();
}

Serializer<CapabilityEnum> _$capabilityEnumSerializer =
    _$CapabilityEnumSerializer();

class _$CapabilityEnumSerializer
    implements PrimitiveSerializer<CapabilityEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'vision': 'vision',
    'textOnly': 'text_only',
    'unknown': 'unknown',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'vision': 'vision',
    'text_only': 'textOnly',
    'unknown': 'unknown',
  };

  @override
  final Iterable<Type> types = const <Type>[CapabilityEnum];
  @override
  final String wireName = 'CapabilityEnum';

  @override
  Object serialize(Serializers serializers, CapabilityEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  CapabilityEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      CapabilityEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
