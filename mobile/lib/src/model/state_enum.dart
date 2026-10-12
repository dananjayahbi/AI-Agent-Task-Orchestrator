//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'state_enum.g.dart';

/// * `draft` - draft * `pending` - pending * `in_progress` - in_progress * `to_be_audited` - to_be_audited * `in_human_review` - in_human_review * `completed` - completed
class StateEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'draft')
  static const StateEnum draft = _$draft;
  @BuiltValueEnumConst(wireName: r'pending')
  static const StateEnum pending = _$pending;
  @BuiltValueEnumConst(wireName: r'in_progress')
  static const StateEnum inProgress = _$inProgress;
  @BuiltValueEnumConst(wireName: r'to_be_audited')
  static const StateEnum toBeAudited = _$toBeAudited;
  @BuiltValueEnumConst(wireName: r'in_human_review')
  static const StateEnum inHumanReview = _$inHumanReview;
  @BuiltValueEnumConst(wireName: r'completed')
  static const StateEnum completed = _$completed;

  static Serializer<StateEnum> get serializer => _$stateEnumSerializer;

  const StateEnum._(String name) : super(name);

  static BuiltSet<StateEnum> get values => _$values;
  static StateEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class StateEnumMixin = Object with _$StateEnumMixin;
