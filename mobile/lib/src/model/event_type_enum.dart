//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'event_type_enum.g.dart';

/// * `in_human_review` - in_human_review * `merge_failure` - merge_failure * `retry_exhaustion` - retry_exhaustion * `completion_digest` - completion_digest
class EventTypeEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'in_human_review')
  static const EventTypeEnum inHumanReview = _$inHumanReview;
  @BuiltValueEnumConst(wireName: r'merge_failure')
  static const EventTypeEnum mergeFailure = _$mergeFailure;
  @BuiltValueEnumConst(wireName: r'retry_exhaustion')
  static const EventTypeEnum retryExhaustion = _$retryExhaustion;
  @BuiltValueEnumConst(wireName: r'completion_digest')
  static const EventTypeEnum completionDigest = _$completionDigest;

  static Serializer<EventTypeEnum> get serializer => _$eventTypeEnumSerializer;

  const EventTypeEnum._(String name) : super(name);

  static BuiltSet<EventTypeEnum> get values => _$values;
  static EventTypeEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class EventTypeEnumMixin = Object with _$EventTypeEnumMixin;
