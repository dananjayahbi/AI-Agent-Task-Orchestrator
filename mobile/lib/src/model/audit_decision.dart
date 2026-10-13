//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'audit_decision.g.dart';

/// The seam's decision the 201 body reports (Section 9.4).
///
/// Properties:
/// * [approve] - True only when the installed Policy Engine approved (T13); the fail-closed default always returns false (invariant 8.3.4).
/// * [reason] - Section 8.4 escalation reason, or null on approval.
@BuiltValue()
abstract class AuditDecision
    implements Built<AuditDecision, AuditDecisionBuilder> {
  /// True only when the installed Policy Engine approved (T13); the fail-closed default always returns false (invariant 8.3.4).
  @BuiltValueField(wireName: r'approve')
  bool get approve;

  /// Section 8.4 escalation reason, or null on approval.
  @BuiltValueField(wireName: r'reason')
  String? get reason;

  AuditDecision._();

  factory AuditDecision([void updates(AuditDecisionBuilder b)]) =
      _$AuditDecision;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AuditDecisionBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AuditDecision> get serializer =>
      _$AuditDecisionSerializer();
}

class _$AuditDecisionSerializer implements PrimitiveSerializer<AuditDecision> {
  @override
  final Iterable<Type> types = const [AuditDecision, _$AuditDecision];

  @override
  final String wireName = r'AuditDecision';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AuditDecision object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'approve';
    yield serializers.serialize(
      object.approve,
      specifiedType: const FullType(bool),
    );
    yield r'reason';
    yield object.reason == null
        ? null
        : serializers.serialize(
            object.reason,
            specifiedType: const FullType.nullable(String),
          );
  }

  @override
  Object serialize(
    Serializers serializers,
    AuditDecision object, {
    FullType specifiedType = FullType.unspecified,
  }) {
    return _serializeProperties(serializers, object,
            specifiedType: specifiedType)
        .toList();
  }

  void _deserializeProperties(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
    required List<Object?> serializedList,
    required AuditDecisionBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'approve':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.approve = valueDes;
          break;
        case r'reason':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.reason = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AuditDecision deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AuditDecisionBuilder();
    final serializedList = (serialized as Iterable<Object?>).toList();
    final unhandled = <Object?>[];
    _deserializeProperties(
      serializers,
      serialized,
      specifiedType: specifiedType,
      serializedList: serializedList,
      unhandled: unhandled,
      result: result,
    );
    return result.build();
  }
}
