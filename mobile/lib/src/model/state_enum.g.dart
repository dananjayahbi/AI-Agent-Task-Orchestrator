// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'state_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const StateEnum _$draft = const StateEnum._('draft');
const StateEnum _$pending = const StateEnum._('pending');
const StateEnum _$inProgress = const StateEnum._('inProgress');
const StateEnum _$toBeAudited = const StateEnum._('toBeAudited');
const StateEnum _$inHumanReview = const StateEnum._('inHumanReview');
const StateEnum _$completed = const StateEnum._('completed');

StateEnum _$valueOf(String name) {
  switch (name) {
    case 'draft':
      return _$draft;
    case 'pending':
      return _$pending;
    case 'inProgress':
      return _$inProgress;
    case 'toBeAudited':
      return _$toBeAudited;
    case 'inHumanReview':
      return _$inHumanReview;
    case 'completed':
      return _$completed;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<StateEnum> _$values = BuiltSet<StateEnum>(const <StateEnum>[
  _$draft,
  _$pending,
  _$inProgress,
  _$toBeAudited,
  _$inHumanReview,
  _$completed,
]);

class _$StateEnumMeta {
  const _$StateEnumMeta();
  StateEnum get draft => _$draft;
  StateEnum get pending => _$pending;
  StateEnum get inProgress => _$inProgress;
  StateEnum get toBeAudited => _$toBeAudited;
  StateEnum get inHumanReview => _$inHumanReview;
  StateEnum get completed => _$completed;
  StateEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<StateEnum> get values => _$values;
}

mixin _$StateEnumMixin {
  // ignore: non_constant_identifier_names
  _$StateEnumMeta get StateEnum => const _$StateEnumMeta();
}

Serializer<StateEnum> _$stateEnumSerializer = _$StateEnumSerializer();

class _$StateEnumSerializer implements PrimitiveSerializer<StateEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'draft': 'draft',
    'pending': 'pending',
    'inProgress': 'in_progress',
    'toBeAudited': 'to_be_audited',
    'inHumanReview': 'in_human_review',
    'completed': 'completed',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'draft': 'draft',
    'pending': 'pending',
    'in_progress': 'inProgress',
    'to_be_audited': 'toBeAudited',
    'in_human_review': 'inHumanReview',
    'completed': 'completed',
  };

  @override
  final Iterable<Type> types = const <Type>[StateEnum];
  @override
  final String wireName = 'StateEnum';

  @override
  Object serialize(Serializers serializers, StateEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  StateEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      StateEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
