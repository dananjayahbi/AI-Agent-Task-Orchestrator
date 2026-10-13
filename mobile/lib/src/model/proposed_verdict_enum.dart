//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'proposed_verdict_enum.g.dart';

/// * `pass` - pass * `flag_risk` - flag_risk * `fail` - fail
class ProposedVerdictEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'pass')
  static const ProposedVerdictEnum pass = _$pass;
  @BuiltValueEnumConst(wireName: r'flag_risk')
  static const ProposedVerdictEnum flagRisk = _$flagRisk;
  @BuiltValueEnumConst(wireName: r'fail')
  static const ProposedVerdictEnum fail = _$fail;

  static Serializer<ProposedVerdictEnum> get serializer =>
      _$proposedVerdictEnumSerializer;

  const ProposedVerdictEnum._(String name) : super(name);

  static BuiltSet<ProposedVerdictEnum> get values => _$values;
  static ProposedVerdictEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class ProposedVerdictEnumMixin = Object
    with _$ProposedVerdictEnumMixin;
