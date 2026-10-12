//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'lease_extension_mode_enum.g.dart';

/// * `checkpoint_only` - checkpoint only * `checkpoint_and_liveness` - checkpoint and liveness
class LeaseExtensionModeEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'checkpoint_only')
  static const LeaseExtensionModeEnum checkpointOnly = _$checkpointOnly;
  @BuiltValueEnumConst(wireName: r'checkpoint_and_liveness')
  static const LeaseExtensionModeEnum checkpointAndLiveness =
      _$checkpointAndLiveness;

  static Serializer<LeaseExtensionModeEnum> get serializer =>
      _$leaseExtensionModeEnumSerializer;

  const LeaseExtensionModeEnum._(String name) : super(name);

  static BuiltSet<LeaseExtensionModeEnum> get values => _$values;
  static LeaseExtensionModeEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class LeaseExtensionModeEnumMixin = Object
    with _$LeaseExtensionModeEnumMixin;
