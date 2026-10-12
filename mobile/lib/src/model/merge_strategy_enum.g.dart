// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'merge_strategy_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const MergeStrategyEnum _$squash = const MergeStrategyEnum._('squash');
const MergeStrategyEnum _$mergeCommit =
    const MergeStrategyEnum._('mergeCommit');
const MergeStrategyEnum _$fastForwardOnly =
    const MergeStrategyEnum._('fastForwardOnly');

MergeStrategyEnum _$valueOf(String name) {
  switch (name) {
    case 'squash':
      return _$squash;
    case 'mergeCommit':
      return _$mergeCommit;
    case 'fastForwardOnly':
      return _$fastForwardOnly;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<MergeStrategyEnum> _$values =
    BuiltSet<MergeStrategyEnum>(const <MergeStrategyEnum>[
  _$squash,
  _$mergeCommit,
  _$fastForwardOnly,
]);

class _$MergeStrategyEnumMeta {
  const _$MergeStrategyEnumMeta();
  MergeStrategyEnum get squash => _$squash;
  MergeStrategyEnum get mergeCommit => _$mergeCommit;
  MergeStrategyEnum get fastForwardOnly => _$fastForwardOnly;
  MergeStrategyEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<MergeStrategyEnum> get values => _$values;
}

mixin _$MergeStrategyEnumMixin {
  // ignore: non_constant_identifier_names
  _$MergeStrategyEnumMeta get MergeStrategyEnum =>
      const _$MergeStrategyEnumMeta();
}

Serializer<MergeStrategyEnum> _$mergeStrategyEnumSerializer =
    _$MergeStrategyEnumSerializer();

class _$MergeStrategyEnumSerializer
    implements PrimitiveSerializer<MergeStrategyEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'squash': 'squash',
    'mergeCommit': 'merge_commit',
    'fastForwardOnly': 'fast_forward_only',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'squash': 'squash',
    'merge_commit': 'mergeCommit',
    'fast_forward_only': 'fastForwardOnly',
  };

  @override
  final Iterable<Type> types = const <Type>[MergeStrategyEnum];
  @override
  final String wireName = 'MergeStrategyEnum';

  @override
  Object serialize(Serializers serializers, MergeStrategyEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  MergeStrategyEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      MergeStrategyEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
