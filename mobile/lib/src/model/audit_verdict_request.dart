//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/verdict_enum.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'audit_verdict_request.g.dart';

/// ``POST /tasks/{id}/audit-verdict`` input (Section 10.5 contract).
///
/// Properties:
/// * [sessionId] - Lease-holding auditor session id (G-18) — the fencing pair's identity half; becomes auditor_session_id (Section 7.2).
/// * [leaseGeneration] - Fencing generation from the claim response (Section 8.6; ADR-012 — the pair every agent mutation carries); a stale value answers LEASE_EXPIRED.
/// * [taskId] - The addressed task id — must equal the path id (Section 10.5 requires task_id in the payload; the path decides, the body echoes).
/// * [verdict] - Section 10.5 enum: pass | flag_risk | fail — the proposal only; the Policy Engine decides the outcome (invariant 8.3.4).  * `pass` - pass * `flag_risk` - flag_risk * `fail` - fail
/// * [confidence] - Section 10.5 / 7.2 confidence (1-5) — the input rule R7 reads.
/// * [notes] - Auditor notes (Section 10.5 `notes` → Section 7.2 `auditor_notes`), shown in the review panel.
/// * [evidence] - Section 10.5 evidence object: required `commands` array (label/command/exit_code per item); `lint_clean`, durations, changed files and diff stats pass through as supplied (FR-AUD-02 — stored verbatim, never reshaped).
/// * [acceptanceCriteriaResults] - Section 10.5 optional array of {criterion, met} — validated here and stored inside the report's evidence JSON (§7.2 gives it no column; recorded reading, MT-3.3-05).
@BuiltValue()
abstract class AuditVerdictRequest
    implements Built<AuditVerdictRequest, AuditVerdictRequestBuilder> {
  /// Lease-holding auditor session id (G-18) — the fencing pair's identity half; becomes auditor_session_id (Section 7.2).
  @BuiltValueField(wireName: r'session_id')
  String get sessionId;

  /// Fencing generation from the claim response (Section 8.6; ADR-012 — the pair every agent mutation carries); a stale value answers LEASE_EXPIRED.
  @BuiltValueField(wireName: r'lease_generation')
  int get leaseGeneration;

  /// The addressed task id — must equal the path id (Section 10.5 requires task_id in the payload; the path decides, the body echoes).
  @BuiltValueField(wireName: r'task_id')
  String get taskId;

  /// Section 10.5 enum: pass | flag_risk | fail — the proposal only; the Policy Engine decides the outcome (invariant 8.3.4).  * `pass` - pass * `flag_risk` - flag_risk * `fail` - fail
  @BuiltValueField(wireName: r'verdict')
  VerdictEnum get verdict;
  // enum verdictEnum {  pass,  flag_risk,  fail,  };

  /// Section 10.5 / 7.2 confidence (1-5) — the input rule R7 reads.
  @BuiltValueField(wireName: r'confidence')
  int get confidence;

  /// Auditor notes (Section 10.5 `notes` → Section 7.2 `auditor_notes`), shown in the review panel.
  @BuiltValueField(wireName: r'notes')
  String? get notes;

  /// Section 10.5 evidence object: required `commands` array (label/command/exit_code per item); `lint_clean`, durations, changed files and diff stats pass through as supplied (FR-AUD-02 — stored verbatim, never reshaped).
  @BuiltValueField(wireName: r'evidence')
  JsonObject? get evidence;

  /// Section 10.5 optional array of {criterion, met} — validated here and stored inside the report's evidence JSON (§7.2 gives it no column; recorded reading, MT-3.3-05).
  @BuiltValueField(wireName: r'acceptance_criteria_results')
  BuiltList<BuiltMap<String, JsonObject?>>? get acceptanceCriteriaResults;

  AuditVerdictRequest._();

  factory AuditVerdictRequest([void updates(AuditVerdictRequestBuilder b)]) =
      _$AuditVerdictRequest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AuditVerdictRequestBuilder b) => b..notes = '';

  @BuiltValueSerializer(custom: true)
  static Serializer<AuditVerdictRequest> get serializer =>
      _$AuditVerdictRequestSerializer();
}

class _$AuditVerdictRequestSerializer
    implements PrimitiveSerializer<AuditVerdictRequest> {
  @override
  final Iterable<Type> types = const [
    AuditVerdictRequest,
    _$AuditVerdictRequest
  ];

  @override
  final String wireName = r'AuditVerdictRequest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AuditVerdictRequest object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'session_id';
    yield serializers.serialize(
      object.sessionId,
      specifiedType: const FullType(String),
    );
    yield r'lease_generation';
    yield serializers.serialize(
      object.leaseGeneration,
      specifiedType: const FullType(int),
    );
    yield r'task_id';
    yield serializers.serialize(
      object.taskId,
      specifiedType: const FullType(String),
    );
    yield r'verdict';
    yield serializers.serialize(
      object.verdict,
      specifiedType: const FullType(VerdictEnum),
    );
    yield r'confidence';
    yield serializers.serialize(
      object.confidence,
      specifiedType: const FullType(int),
    );
    if (object.notes != null) {
      yield r'notes';
      yield serializers.serialize(
        object.notes,
        specifiedType: const FullType(String),
      );
    }
    yield r'evidence';
    yield object.evidence == null
        ? null
        : serializers.serialize(
            object.evidence,
            specifiedType: const FullType.nullable(JsonObject),
          );
    if (object.acceptanceCriteriaResults != null) {
      yield r'acceptance_criteria_results';
      yield serializers.serialize(
        object.acceptanceCriteriaResults,
        specifiedType: const FullType.nullable(BuiltList, [
          FullType(BuiltMap, [FullType(String), FullType.nullable(JsonObject)])
        ]),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    AuditVerdictRequest object, {
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
    required AuditVerdictRequestBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'session_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.sessionId = valueDes;
          break;
        case r'lease_generation':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.leaseGeneration = valueDes;
          break;
        case r'task_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.taskId = valueDes;
          break;
        case r'verdict':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(VerdictEnum),
          ) as VerdictEnum;
          result.verdict = valueDes;
          break;
        case r'confidence':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.confidence = valueDes;
          break;
        case r'notes':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.notes = valueDes;
          break;
        case r'evidence':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(JsonObject),
          ) as JsonObject?;
          if (valueDes == null) continue;
          result.evidence = valueDes;
          break;
        case r'acceptance_criteria_results':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(BuiltList, [
              FullType(
                  BuiltMap, [FullType(String), FullType.nullable(JsonObject)])
            ]),
          ) as BuiltList<BuiltMap<String, JsonObject?>>?;
          if (valueDes == null) continue;
          result.acceptanceCriteriaResults.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AuditVerdictRequest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AuditVerdictRequestBuilder();
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
