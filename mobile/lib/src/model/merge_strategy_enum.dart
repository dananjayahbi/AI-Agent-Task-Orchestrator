//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'merge_strategy_enum.g.dart';

/// * `squash` - squash * `merge_commit` - merge commit * `fast_forward_only` - fast forward only
class MergeStrategyEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'squash')
  static const MergeStrategyEnum squash = _$squash;
  @BuiltValueEnumConst(wireName: r'merge_commit')
  static const MergeStrategyEnum mergeCommit = _$mergeCommit;
  @BuiltValueEnumConst(wireName: r'fast_forward_only')
  static const MergeStrategyEnum fastForwardOnly = _$fastForwardOnly;

  static Serializer<MergeStrategyEnum> get serializer =>
      _$mergeStrategyEnumSerializer;

  const MergeStrategyEnum._(String name) : super(name);

  static BuiltSet<MergeStrategyEnum> get values => _$values;
  static MergeStrategyEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class MergeStrategyEnumMixin = Object with _$MergeStrategyEnumMixin;
