//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/audit_report.dart';
import 'package:orchestrator_mobile/src/model/audit_decision.dart';
import 'package:orchestrator_mobile/src/model/verdict_task_state.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'audit_verdict_response.g.dart';

/// The frozen verdict response — report + outcome (Section 10.5).
///
/// Properties:
/// * [report] - The stored Section 7.2 row.
/// * [task] - Post-transition task identity — the outcome the agent is told (decided by the seam, never by this endpoint).
/// * [trigger] - Which Section 8.2 row fired: audit_verdict_escalated (T14) or audit_verdict_pass (T13, engine-only).
/// * [decision] - The Policy Engine seam's decision (approve/escalate + reason).
@BuiltValue()
abstract class AuditVerdictResponse
    implements Built<AuditVerdictResponse, AuditVerdictResponseBuilder> {
  /// The stored Section 7.2 row.
  @BuiltValueField(wireName: r'report')
  AuditReport get report;

  /// Post-transition task identity — the outcome the agent is told (decided by the seam, never by this endpoint).
  @BuiltValueField(wireName: r'task')
  VerdictTaskState get task;

  /// Which Section 8.2 row fired: audit_verdict_escalated (T14) or audit_verdict_pass (T13, engine-only).
  @BuiltValueField(wireName: r'trigger')
  String get trigger;

  /// The Policy Engine seam's decision (approve/escalate + reason).
  @BuiltValueField(wireName: r'decision')
  AuditDecision get decision;

  AuditVerdictResponse._();

  factory AuditVerdictResponse([void updates(AuditVerdictResponseBuilder b)]) =
      _$AuditVerdictResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AuditVerdictResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AuditVerdictResponse> get serializer =>
      _$AuditVerdictResponseSerializer();
}

class _$AuditVerdictResponseSerializer
    implements PrimitiveSerializer<AuditVerdictResponse> {
  @override
  final Iterable<Type> types = const [
    AuditVerdictResponse,
    _$AuditVerdictResponse
  ];

  @override
  final String wireName = r'AuditVerdictResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AuditVerdictResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'report';
    yield serializers.serialize(
      object.report,
      specifiedType: const FullType(AuditReport),
    );
    yield r'task';
    yield serializers.serialize(
      object.task,
      specifiedType: const FullType(VerdictTaskState),
    );
    yield r'trigger';
    yield serializers.serialize(
      object.trigger,
      specifiedType: const FullType(String),
    );
    yield r'decision';
    yield serializers.serialize(
      object.decision,
      specifiedType: const FullType(AuditDecision),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    AuditVerdictResponse object, {
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
    required AuditVerdictResponseBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'report':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(AuditReport),
          ) as AuditReport;
          result.report.replace(valueDes);
          break;
        case r'task':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(VerdictTaskState),
          ) as VerdictTaskState;
          result.task.replace(valueDes);
          break;
        case r'trigger':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.trigger = valueDes;
          break;
        case r'decision':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(AuditDecision),
          ) as AuditDecision;
          result.decision.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AuditVerdictResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AuditVerdictResponseBuilder();
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
