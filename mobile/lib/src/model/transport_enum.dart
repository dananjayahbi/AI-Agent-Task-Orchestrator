//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'transport_enum.g.dart';

/// * `stdio` - stdio * `http` - http
class TransportEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'stdio')
  static const TransportEnum stdio = _$stdio;
  @BuiltValueEnumConst(wireName: r'http')
  static const TransportEnum http = _$http;

  static Serializer<TransportEnum> get serializer => _$transportEnumSerializer;

  const TransportEnum._(String name) : super(name);

  static BuiltSet<TransportEnum> get values => _$values;
  static TransportEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class TransportEnumMixin = Object with _$TransportEnumMixin;
