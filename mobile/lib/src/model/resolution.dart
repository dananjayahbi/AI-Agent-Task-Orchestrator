//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'resolution.g.dart';

/// One stored resolution — the Section 7.2 field list, as returned.
///
/// Properties:
/// * [id] - Server-generated row identity (7.2).
/// * [taskId] - The addressed task (Section 7.2).
/// * [attemptNumber] - The submission attempt this row answers (Section 7.2; unique per task).
/// * [branchName] - Branch the patch came from (7.2).
/// * [commitSha] - Commit the submission points at (7.2).
/// * [executionSummary]
/// * [diffSummary] - Authoritative {files, insertions, deletions} parsed from the stored patch (Section 9.7).
/// * [changedFiles] - Authoritative repo-relative paths touched (Section 9.7).
/// * [requiresHumanAttention] - The coder's self-flag (Section 7.2; T8's guard input).
/// * [riskJustification]
/// * [submittedBySession] - Bridge session that submitted (Section 7.2; always the lease owner).
/// * [submittedAt] - Server clock at insertion (P7).
@BuiltValue()
abstract class Resolution implements Built<Resolution, ResolutionBuilder> {
  /// Server-generated row identity (7.2).
  @BuiltValueField(wireName: r'id')
  String get id;

  /// The addressed task (Section 7.2).
  @BuiltValueField(wireName: r'task_id')
  String get taskId;

  /// The submission attempt this row answers (Section 7.2; unique per task).
  @BuiltValueField(wireName: r'attempt_number')
  int get attemptNumber;

  /// Branch the patch came from (7.2).
  @BuiltValueField(wireName: r'branch_name')
  String get branchName;

  /// Commit the submission points at (7.2).
  @BuiltValueField(wireName: r'commit_sha')
  String get commitSha;

  @BuiltValueField(wireName: r'execution_summary')
  String get executionSummary;

  /// Authoritative {files, insertions, deletions} parsed from the stored patch (Section 9.7).
  @BuiltValueField(wireName: r'diff_summary')
  JsonObject? get diffSummary;

  /// Authoritative repo-relative paths touched (Section 9.7).
  @BuiltValueField(wireName: r'changed_files')
  BuiltList<String> get changedFiles;

  /// The coder's self-flag (Section 7.2; T8's guard input).
  @BuiltValueField(wireName: r'requires_human_attention')
  bool get requiresHumanAttention;

  @BuiltValueField(wireName: r'risk_justification')
  String get riskJustification;

  /// Bridge session that submitted (Section 7.2; always the lease owner).
  @BuiltValueField(wireName: r'submitted_by_session')
  String get submittedBySession;

  /// Server clock at insertion (P7).
  @BuiltValueField(wireName: r'submitted_at')
  DateTime get submittedAt;

  Resolution._();

  factory Resolution([void updates(ResolutionBuilder b)]) = _$Resolution;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ResolutionBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<Resolution> get serializer => _$ResolutionSerializer();
}

class _$ResolutionSerializer implements PrimitiveSerializer<Resolution> {
  @override
  final Iterable<Type> types = const [Resolution, _$Resolution];

  @override
  final String wireName = r'Resolution';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    Resolution object, {
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
    yield r'attempt_number';
    yield serializers.serialize(
      object.attemptNumber,
      specifiedType: const FullType(int),
    );
    yield r'branch_name';
    yield serializers.serialize(
      object.branchName,
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
    yield r'diff_summary';
    yield object.diffSummary == null
        ? null
        : serializers.serialize(
            object.diffSummary,
            specifiedType: const FullType.nullable(JsonObject),
          );
    yield r'changed_files';
    yield serializers.serialize(
      object.changedFiles,
      specifiedType: const FullType(BuiltList, [FullType(String)]),
    );
    yield r'requires_human_attention';
    yield serializers.serialize(
      object.requiresHumanAttention,
      specifiedType: const FullType(bool),
    );
    yield r'risk_justification';
    yield serializers.serialize(
      object.riskJustification,
      specifiedType: const FullType(String),
    );
    yield r'submitted_by_session';
    yield serializers.serialize(
      object.submittedBySession,
      specifiedType: const FullType(String),
    );
    yield r'submitted_at';
    yield serializers.serialize(
      object.submittedAt,
      specifiedType: const FullType(DateTime),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    Resolution object, {
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
    required ResolutionBuilder result,
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
        case r'attempt_number':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.attemptNumber = valueDes;
          break;
        case r'branch_name':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.branchName = valueDes;
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
        case r'diff_summary':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(JsonObject),
          ) as JsonObject?;
          if (valueDes == null) continue;
          result.diffSummary = valueDes;
          break;
        case r'changed_files':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(BuiltList, [FullType(String)]),
          ) as BuiltList<String>;
          result.changedFiles.replace(valueDes);
          break;
        case r'requires_human_attention':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.requiresHumanAttention = valueDes;
          break;
        case r'risk_justification':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.riskJustification = valueDes;
          break;
        case r'submitted_by_session':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.submittedBySession = valueDes;
          break;
        case r'submitted_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.submittedAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  Resolution deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ResolutionBuilder();
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
