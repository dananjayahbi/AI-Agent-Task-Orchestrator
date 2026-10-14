// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'result_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const ResultEnum _$succeeded = const ResultEnum._('succeeded');
const ResultEnum _$conflict = const ResultEnum._('conflict');
const ResultEnum _$failed = const ResultEnum._('failed');

ResultEnum _$valueOf(String name) {
  switch (name) {
    case 'succeeded':
      return _$succeeded;
    case 'conflict':
      return _$conflict;
    case 'failed':
      return _$failed;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<ResultEnum> _$values = BuiltSet<ResultEnum>(const <ResultEnum>[
  _$succeeded,
  _$conflict,
  _$failed,
]);

class _$ResultEnumMeta {
  const _$ResultEnumMeta();
  ResultEnum get succeeded => _$succeeded;
  ResultEnum get conflict => _$conflict;
  ResultEnum get failed => _$failed;
  ResultEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<ResultEnum> get values => _$values;
}

mixin _$ResultEnumMixin {
  // ignore: non_constant_identifier_names
  _$ResultEnumMeta get ResultEnum => const _$ResultEnumMeta();
}

Serializer<ResultEnum> _$resultEnumSerializer = _$ResultEnumSerializer();

class _$ResultEnumSerializer implements PrimitiveSerializer<ResultEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'succeeded': 'succeeded',
    'conflict': 'conflict',
    'failed': 'failed',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'succeeded': 'succeeded',
    'conflict': 'conflict',
    'failed': 'failed',
  };

  @override
  final Iterable<Type> types = const <Type>[ResultEnum];
  @override
  final String wireName = 'ResultEnum';

  @override
  Object serialize(Serializers serializers, ResultEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  ResultEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      ResultEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
