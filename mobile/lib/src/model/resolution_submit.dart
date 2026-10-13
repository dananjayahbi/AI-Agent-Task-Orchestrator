//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'resolution_submit.g.dart';

/// ``POST /tasks/{id}/resolution`` input (Section 10.5 tool contract).
///
/// Properties:
/// * [sessionId] - Lease-holding session id (G-18) — the fencing pair's identity half; becomes submitted_by_session (Section 7.2).
/// * [leaseGeneration] - Fencing generation from the claim response (Section 8.6; ADR-012); a stale value answers LEASE_EXPIRED.
/// * [gitBranch] - Verified branch the patch was captured from (Section 10.5; stored as the Section 7.2 branch_name).
/// * [commitSha] - Commit the submission points at (Section 10.5; the bridge verified it matches the branch — stored verbatim).
/// * [executionSummary] - The coder's summary of what ran (Section 10.5).
/// * [requiresHumanAttention] - The coder's self-flag (Section 10.5) — true routes the submission to T8 with review_reason self_flagged (8.2/8.4).
/// * [riskJustification] - The coder's justification when self-flagging (Section 7.2).
/// * [patch_] - The captured unified patch, branch vs. default-branch merge-base (Section 9.7) — parsed server-side for the authoritative changed_files and diff_summary; subject to the 5 MB cap with a degraded stats-only path, never a rejection. Whitespace (the trailing newline) is content: the sha256 the bridge computes locally must match the bytes stored here.
/// * [changedFiles] - Bridge-captured file list (Section 10.5) — provisional: the server's patch parse replaces it outright (Section 9.7).
/// * [diffSummary] - Bridge-captured stats (Section 10.5) — provisional: the server's patch parse replaces it outright (Section 9.7).
@BuiltValue()
abstract class ResolutionSubmit
    implements Built<ResolutionSubmit, ResolutionSubmitBuilder> {
  /// Lease-holding session id (G-18) — the fencing pair's identity half; becomes submitted_by_session (Section 7.2).
  @BuiltValueField(wireName: r'session_id')
  String get sessionId;

  /// Fencing generation from the claim response (Section 8.6; ADR-012); a stale value answers LEASE_EXPIRED.
  @BuiltValueField(wireName: r'lease_generation')
  int get leaseGeneration;

  /// Verified branch the patch was captured from (Section 10.5; stored as the Section 7.2 branch_name).
  @BuiltValueField(wireName: r'git_branch')
  String get gitBranch;

  /// Commit the submission points at (Section 10.5; the bridge verified it matches the branch — stored verbatim).
  @BuiltValueField(wireName: r'commit_sha')
  String get commitSha;

  /// The coder's summary of what ran (Section 10.5).
  @BuiltValueField(wireName: r'execution_summary')
  String get executionSummary;

  /// The coder's self-flag (Section 10.5) — true routes the submission to T8 with review_reason self_flagged (8.2/8.4).
  @BuiltValueField(wireName: r'requires_human_attention')
  bool? get requiresHumanAttention;

  /// The coder's justification when self-flagging (Section 7.2).
  @BuiltValueField(wireName: r'risk_justification')
  String? get riskJustification;

  /// The captured unified patch, branch vs. default-branch merge-base (Section 9.7) — parsed server-side for the authoritative changed_files and diff_summary; subject to the 5 MB cap with a degraded stats-only path, never a rejection. Whitespace (the trailing newline) is content: the sha256 the bridge computes locally must match the bytes stored here.
  @BuiltValueField(wireName: r'patch')
  String get patch_;

  /// Bridge-captured file list (Section 10.5) — provisional: the server's patch parse replaces it outright (Section 9.7).
  @BuiltValueField(wireName: r'changed_files')
  BuiltList<String>? get changedFiles;

  /// Bridge-captured stats (Section 10.5) — provisional: the server's patch parse replaces it outright (Section 9.7).
  @BuiltValueField(wireName: r'diff_summary')
  BuiltMap<String, JsonObject?>? get diffSummary;

  ResolutionSubmit._();

  factory ResolutionSubmit([void updates(ResolutionSubmitBuilder b)]) =
      _$ResolutionSubmit;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ResolutionSubmitBuilder b) => b
    ..requiresHumanAttention = false
    ..riskJustification = '';

  @BuiltValueSerializer(custom: true)
  static Serializer<ResolutionSubmit> get serializer =>
      _$ResolutionSubmitSerializer();
}

class _$ResolutionSubmitSerializer
    implements PrimitiveSerializer<ResolutionSubmit> {
  @override
  final Iterable<Type> types = const [ResolutionSubmit, _$ResolutionSubmit];

  @override
  final String wireName = r'ResolutionSubmit';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ResolutionSubmit object, {
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
    yield r'git_branch';
    yield serializers.serialize(
      object.gitBranch,
      specifiedType: const FullType(String),
    );
    yield r'commit_sha';
    yield serializers.serialize(
      object.commitSha,
      specifiedType: const FullType(String),
    );
    yield r'execution_summary';
    yield serializers.serialize(
      object.executionSummary,
      specifiedType: const FullType(String),
    );
    if (object.requiresHumanAttention != null) {
      yield r'requires_human_attention';
      yield serializers.serialize(
        object.requiresHumanAttention,
        specifiedType: const FullType(bool),
      );
    }
    if (object.riskJustification != null) {
      yield r'risk_justification';
      yield serializers.serialize(
        object.riskJustification,
        specifiedType: const FullType(String),
      );
    }
    yield r'patch';
    yield serializers.serialize(
      object.patch_,
      specifiedType: const FullType(String),
    );
    if (object.changedFiles != null) {
      yield r'changed_files';
      yield serializers.serialize(
        object.changedFiles,
        specifiedType: const FullType.nullable(BuiltList, [FullType(String)]),
      );
    }
    if (object.diffSummary != null) {
      yield r'diff_summary';
      yield serializers.serialize(
        object.diffSummary,
        specifiedType: const FullType.nullable(
            BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    ResolutionSubmit object, {
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
    required ResolutionSubmitBuilder result,
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
        case r'git_branch':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.gitBranch = valueDes;
          break;
        case r'commit_sha':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.commitSha = valueDes;
          break;
        case r'execution_summary':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.executionSummary = valueDes;
          break;
        case r'requires_human_attention':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(bool),
          ) as bool?;
          if (valueDes == null) continue;
          result.requiresHumanAttention = valueDes;
          break;
        case r'risk_justification':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.riskJustification = valueDes;
          break;
        case r'patch':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.patch_ = valueDes;
          break;
        case r'changed_files':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.changedFiles.replace(valueDes);
          break;
        case r'diff_summary':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(
                BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
          ) as BuiltMap<String, JsonObject?>?;
          if (valueDes == null) continue;
          result.diffSummary.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ResolutionSubmit deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ResolutionSubmitBuilder();
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
