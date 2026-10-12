// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'checkpoint_create_kind_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const CheckpointCreateKindEnum _$progress =
    const CheckpointCreateKindEnum._('progress');
const CheckpointCreateKindEnum _$liveness =
    const CheckpointCreateKindEnum._('liveness');
const CheckpointCreateKindEnum _$system =
    const CheckpointCreateKindEnum._('system');

CheckpointCreateKindEnum _$valueOf(String name) {
  switch (name) {
    case 'progress':
      return _$progress;
    case 'liveness':
      return _$liveness;
    case 'system':
      return _$system;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<CheckpointCreateKindEnum> _$values =
    BuiltSet<CheckpointCreateKindEnum>(const <CheckpointCreateKindEnum>[
  _$progress,
  _$liveness,
  _$system,
]);

class _$CheckpointCreateKindEnumMeta {
  const _$CheckpointCreateKindEnumMeta();
  CheckpointCreateKindEnum get progress => _$progress;
  CheckpointCreateKindEnum get liveness => _$liveness;
  CheckpointCreateKindEnum get system => _$system;
  CheckpointCreateKindEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<CheckpointCreateKindEnum> get values => _$values;
}

mixin _$CheckpointCreateKindEnumMixin {
  // ignore: non_constant_identifier_names
  _$CheckpointCreateKindEnumMeta get CheckpointCreateKindEnum =>
      const _$CheckpointCreateKindEnumMeta();
}

Serializer<CheckpointCreateKindEnum> _$checkpointCreateKindEnumSerializer =
    _$CheckpointCreateKindEnumSerializer();

class _$CheckpointCreateKindEnumSerializer
    implements PrimitiveSerializer<CheckpointCreateKindEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'progress': 'progress',
    'liveness': 'liveness',
    'system': 'system',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'progress': 'progress',
    'liveness': 'liveness',
    'system': 'system',
  };

  @override
  final Iterable<Type> types = const <Type>[CheckpointCreateKindEnum];
  @override
  final String wireName = 'CheckpointCreateKindEnum';

  @override
  Object serialize(Serializers serializers, CheckpointCreateKindEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  CheckpointCreateKindEnum deserialize(
          Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      CheckpointCreateKindEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
