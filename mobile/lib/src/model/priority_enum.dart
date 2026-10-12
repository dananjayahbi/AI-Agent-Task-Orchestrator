//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'priority_enum.g.dart';

/// * `urgent` - urgent * `high` - high * `medium` - medium * `low` - low
class PriorityEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'urgent')
  static const PriorityEnum urgent = _$urgent;
  @BuiltValueEnumConst(wireName: r'high')
  static const PriorityEnum high = _$high;
  @BuiltValueEnumConst(wireName: r'medium')
  static const PriorityEnum medium = _$medium;
  @BuiltValueEnumConst(wireName: r'low')
  static const PriorityEnum low = _$low;

  static Serializer<PriorityEnum> get serializer => _$priorityEnumSerializer;

  const PriorityEnum._(String name) : super(name);

  static BuiltSet<PriorityEnum> get values => _$values;
  static PriorityEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class PriorityEnumMixin = Object with _$PriorityEnumMixin;
