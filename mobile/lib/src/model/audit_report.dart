//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/proposed_verdict_enum.dart';
import 'package:orchestrator_mobile/src/model/policy_decision_enum.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'audit_report.g.dart';

/// One stored report — the Section 7.2 field list, as returned.
///
/// Properties:
/// * [id] - Server-generated row identity (Section 7.2).
/// * [taskId] - The audited task (Section 7.2).
/// * [resolutionId] - The audited submission (Section 7.2 — one report per verdict, accumulating across T12 audit retries).
/// * [auditorSessionId] - Bridge session that audited (Section 7.2; G-18 — always the auditor lease owner at submit time).
/// * [evidence] - Section 7.2 evidence JSON — the Section 10.5 structure as supplied (commands with exit codes, lint_clean, stats…).
/// * [confidence] - Section 7.2 confidence (1-5; DB-constrained).
/// * [auditorNotes]
/// * [proposedVerdict] - Section 10.5 enum the auditor proposed; the engine decides.  * `pass` - pass * `flag_risk` - flag_risk * `fail` - fail
/// * [policyDecision] - Section 9.4 engine output (approve | escalate) — null until the Policy Engine writes it (MT-3.4-06), never faked here.  * `approve` - approve * `escalate` - escalate
/// * [policyRuleResults] - Section 7.2/9.4 per-rule pass/fail — null until the engine persists it (MT-3.4-06), never faked here.
/// * [createdAt] - Server clock at insertion (P7).
@BuiltValue()
abstract class AuditReport implements Built<AuditReport, AuditReportBuilder> {
  /// Server-generated row identity (Section 7.2).
  @BuiltValueField(wireName: r'id')
  String get id;

  /// The audited task (Section 7.2).
  @BuiltValueField(wireName: r'task_id')
  String get taskId;

  /// The audited submission (Section 7.2 — one report per verdict, accumulating across T12 audit retries).
  @BuiltValueField(wireName: r'resolution_id')
  String get resolutionId;

  /// Bridge session that audited (Section 7.2; G-18 — always the auditor lease owner at submit time).
  @BuiltValueField(wireName: r'auditor_session_id')
  String get auditorSessionId;

  /// Section 7.2 evidence JSON — the Section 10.5 structure as supplied (commands with exit codes, lint_clean, stats…).
  @BuiltValueField(wireName: r'evidence')
  JsonObject? get evidence;

  /// Section 7.2 confidence (1-5; DB-constrained).
  @BuiltValueField(wireName: r'confidence')
  int get confidence;

  @BuiltValueField(wireName: r'auditor_notes')
  String get auditorNotes;

  /// Section 10.5 enum the auditor proposed; the engine decides.  * `pass` - pass * `flag_risk` - flag_risk * `fail` - fail
  @BuiltValueField(wireName: r'proposed_verdict')
  ProposedVerdictEnum get proposedVerdict;
  // enum proposedVerdictEnum {  pass,  flag_risk,  fail,  };

  /// Section 9.4 engine output (approve | escalate) — null until the Policy Engine writes it (MT-3.4-06), never faked here.  * `approve` - approve * `escalate` - escalate
  @BuiltValueField(wireName: r'policy_decision')
  PolicyDecisionEnum? get policyDecision;
  // enum policyDecisionEnum {  approve,  escalate,  };

  /// Section 7.2/9.4 per-rule pass/fail — null until the engine persists it (MT-3.4-06), never faked here.
  @BuiltValueField(wireName: r'policy_rule_results')
  JsonObject? get policyRuleResults;

  /// Server clock at insertion (P7).
  @BuiltValueField(wireName: r'created_at')
  DateTime get createdAt;

  AuditReport._();

  factory AuditReport([void updates(AuditReportBuilder b)]) = _$AuditReport;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AuditReportBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AuditReport> get serializer => _$AuditReportSerializer();
}

class _$AuditReportSerializer implements PrimitiveSerializer<AuditReport> {
  @override
  final Iterable<Type> types = const [AuditReport, _$AuditReport];

  @override
  final String wireName = r'AuditReport';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AuditReport object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'task_id';
    yield serializers.serialize(
      object.taskId,
      specifiedType: const FullType(String),
    );
    yield r'resolution_id';
    yield serializers.serialize(
      object.resolutionId,
      specifiedType: const FullType(String),
    );
    yield r'auditor_session_id';
    yield serializers.serialize(
      object.auditorSessionId,
      specifiedType: const FullType(String),
    );
    yield r'evidence';
    yield object.evidence == null
        ? null
        : serializers.serialize(
            object.evidence,
            specifiedType: const FullType.nullable(JsonObject),
          );
    yield r'confidence';
    yield serializers.serialize(
      object.confidence,
      specifiedType: const FullType(int),
    );
    yield r'auditor_notes';
    yield serializers.serialize(
      object.auditorNotes,
      specifiedType: const FullType(String),
    );
    yield r'proposed_verdict';
    yield serializers.serialize(
      object.proposedVerdict,
      specifiedType: const FullType(ProposedVerdictEnum),
    );
    yield r'policy_decision';
    yield object.policyDecision == null
        ? null
        : serializers.serialize(
            object.policyDecision,
            specifiedType: const FullType.nullable(PolicyDecisionEnum),
          );
    yield r'policy_rule_results';
    yield object.policyRuleResults == null
        ? null
        : serializers.serialize(
            object.policyRuleResults,
            specifiedType: const FullType.nullable(JsonObject),
          );
    yield r'created_at';
    yield serializers.serialize(
      object.createdAt,
      specifiedType: const FullType(DateTime),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    AuditReport object, {
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
    required AuditReportBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.id = valueDes;
          break;
        case r'task_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.taskId = valueDes;
          break;
        case r'resolution_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.resolutionId = valueDes;
          break;
        case r'auditor_session_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.auditorSessionId = valueDes;
          break;
        case r'evidence':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(JsonObject),
          ) as JsonObject?;
          if (valueDes == null) continue;
          result.evidence = valueDes;
          break;
        case r'confidence':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.confidence = valueDes;
          break;
        case r'auditor_notes':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.auditorNotes = valueDes;
          break;
        case r'proposed_verdict':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(ProposedVerdictEnum),
          ) as ProposedVerdictEnum;
          result.proposedVerdict = valueDes;
          break;
        case r'policy_decision':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(PolicyDecisionEnum),
          ) as PolicyDecisionEnum?;
          if (valueDes == null) continue;
          result.policyDecision = valueDes;
          break;
        case r'policy_rule_results':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(JsonObject),
          ) as JsonObject?;
          if (valueDes == null) continue;
          result.policyRuleResults = valueDes;
          break;
        case r'created_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.createdAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AuditReport deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AuditReportBuilder();
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
