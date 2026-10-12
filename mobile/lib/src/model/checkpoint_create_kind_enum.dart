//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'checkpoint_create_kind_enum.g.dart';

/// * `progress` - progress * `liveness` - liveness * `system` - system
class CheckpointCreateKindEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'progress')
  static const CheckpointCreateKindEnum progress = _$progress;
  @BuiltValueEnumConst(wireName: r'liveness')
  static const CheckpointCreateKindEnum liveness = _$liveness;
  @BuiltValueEnumConst(wireName: r'system')
  static const CheckpointCreateKindEnum system = _$system;

  static Serializer<CheckpointCreateKindEnum> get serializer =>
      _$checkpointCreateKindEnumSerializer;

  const CheckpointCreateKindEnum._(String name) : super(name);

  static BuiltSet<CheckpointCreateKindEnum> get values => _$values;
  static CheckpointCreateKindEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class CheckpointCreateKindEnumMixin = Object
    with _$CheckpointCreateKindEnumMixin;
