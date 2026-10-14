//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'decision_enum.g.dart';

/// * `approve` - approve * `request_changes` - request_changes * `reassign` - reassign
class DecisionEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'approve')
  static const DecisionEnum approve = _$approve;
  @BuiltValueEnumConst(wireName: r'request_changes')
  static const DecisionEnum requestChanges = _$requestChanges;
  @BuiltValueEnumConst(wireName: r'reassign')
  static const DecisionEnum reassign = _$reassign;

  static Serializer<DecisionEnum> get serializer => _$decisionEnumSerializer;

  const DecisionEnum._(String name) : super(name);

  static BuiltSet<DecisionEnum> get values => _$values;
  static DecisionEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class DecisionEnumMixin = Object with _$DecisionEnumMixin;
