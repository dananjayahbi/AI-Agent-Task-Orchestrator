//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'kind_e0d_enum.g.dart';

/// * `owner_session` - owner session * `agent` - agent * `device` - device
class KindE0dEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'owner_session')
  static const KindE0dEnum ownerSession = _$ownerSession;
  @BuiltValueEnumConst(wireName: r'agent')
  static const KindE0dEnum agent = _$agent;
  @BuiltValueEnumConst(wireName: r'device')
  static const KindE0dEnum device = _$device;

  static Serializer<KindE0dEnum> get serializer => _$kindE0dEnumSerializer;

  const KindE0dEnum._(String name) : super(name);

  static BuiltSet<KindE0dEnum> get values => _$values;
  static KindE0dEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class KindE0dEnumMixin = Object with _$KindE0dEnumMixin;
