//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/priority_enum.dart';
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/state_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'task.g.dart';

/// GET representation of a task — Section 7.2 fields, in plan order.
///
/// Properties:
/// * [id] - {PID}-T{index} (Section 7.3); server-assigned, immutable.
/// * [projectId] - Section 7.2 project_id FK — never changes (7.4 rule 4).
/// * [title]
/// * [description] - Markdown description (FR-TSK-02).
/// * [acceptanceCriteria]
/// * [targetScope] - Repo-relative path globs (Section 12.3).
/// * [testCommand]
/// * [priority]
/// * [state] - Canonical G-01 state (ADR-010); draft on create (T1).  * `draft` - draft * `pending` - pending * `in_progress` - in_progress * `to_be_audited` - to_be_audited * `in_human_review` - in_human_review * `completed` - completed
/// * [version] - FR-TSK-06: incremented on every change; PATCH echoes it.
/// * [workerAgentId] - Lease holder (WP-1.6).
/// * [workerSessionId] - Bridge session (G-18).
/// * [claimedRole] - coder | auditor | null.
/// * [leaseAcquiredAt]
/// * [leaseExpiresAt]
/// * [lastCheckpointAt]
/// * [failureRetryCount]
/// * [attemptNumber]
/// * [auditRequired] - Copied from the project policy at creation (Section 7.2).
/// * [reviewReason] - Section 8.4 enum | null.
/// * [latestFeedback]
/// * [mergeStatus] - none | pending | merging | merged | conflict | failed.
/// * [archivedAt] - Soft-archive marker; archived tasks stay readable (7.3).
/// * [createdBy]
/// * [createdAt]
/// * [updatedAt]
/// * [dependsOn] - Section 7.1 N:N relation (FR-TSK-07): the task ids this task waits on, ordered by id. Server-managed — written through the `depends_on` field of POST/PATCH (replace-the-set), read here.
@BuiltValue()
abstract class Task implements Built<Task, TaskBuilder> {
  /// {PID}-T{index} (Section 7.3); server-assigned, immutable.
  @BuiltValueField(wireName: r'id')
  String get id;

  /// Section 7.2 project_id FK — never changes (7.4 rule 4).
  @BuiltValueField(wireName: r'project_id')
  String get projectId;

  @BuiltValueField(wireName: r'title')
  String get title;

  /// Markdown description (FR-TSK-02).
  @BuiltValueField(wireName: r'description')
  String get description;

  @BuiltValueField(wireName: r'acceptance_criteria')
  BuiltList<String> get acceptanceCriteria;

  /// Repo-relative path globs (Section 12.3).
  @BuiltValueField(wireName: r'target_scope')
  BuiltList<String> get targetScope;

  @BuiltValueField(wireName: r'test_command')
  String get testCommand;

  @BuiltValueField(wireName: r'priority')
  PriorityEnum get priority;
  // enum priorityEnum {  urgent,  high,  medium,  low,  };

  /// Canonical G-01 state (ADR-010); draft on create (T1).  * `draft` - draft * `pending` - pending * `in_progress` - in_progress * `to_be_audited` - to_be_audited * `in_human_review` - in_human_review * `completed` - completed
  @BuiltValueField(wireName: r'state')
  StateEnum get state;
  // enum stateEnum {  draft,  pending,  in_progress,  to_be_audited,  in_human_review,  completed,  };

  /// FR-TSK-06: incremented on every change; PATCH echoes it.
  @BuiltValueField(wireName: r'version')
  int get version;

  /// Lease holder (WP-1.6).
  @BuiltValueField(wireName: r'worker_agent_id')
  String? get workerAgentId;

  /// Bridge session (G-18).
  @BuiltValueField(wireName: r'worker_session_id')
  String? get workerSessionId;

  /// coder | auditor | null.
  @BuiltValueField(wireName: r'claimed_role')
  String? get claimedRole;

  @BuiltValueField(wireName: r'lease_acquired_at')
  DateTime? get leaseAcquiredAt;

  @BuiltValueField(wireName: r'lease_expires_at')
  DateTime? get leaseExpiresAt;

  @BuiltValueField(wireName: r'last_checkpoint_at')
  DateTime? get lastCheckpointAt;

  @BuiltValueField(wireName: r'failure_retry_count')
  int get failureRetryCount;

  @BuiltValueField(wireName: r'attempt_number')
  int get attemptNumber;

  /// Copied from the project policy at creation (Section 7.2).
  @BuiltValueField(wireName: r'audit_required')
  bool get auditRequired;

  /// Section 8.4 enum | null.
  @BuiltValueField(wireName: r'review_reason')
  String? get reviewReason;

  @BuiltValueField(wireName: r'latest_feedback')
  String get latestFeedback;

  /// none | pending | merging | merged | conflict | failed.
  @BuiltValueField(wireName: r'merge_status')
  String get mergeStatus;

  /// Soft-archive marker; archived tasks stay readable (7.3).
  @BuiltValueField(wireName: r'archived_at')
  DateTime? get archivedAt;

  @BuiltValueField(wireName: r'created_by')
  String? get createdBy;

  @BuiltValueField(wireName: r'created_at')
  DateTime get createdAt;

  @BuiltValueField(wireName: r'updated_at')
  DateTime get updatedAt;

  /// Section 7.1 N:N relation (FR-TSK-07): the task ids this task waits on, ordered by id. Server-managed — written through the `depends_on` field of POST/PATCH (replace-the-set), read here.
  @BuiltValueField(wireName: r'depends_on')
  BuiltList<String> get dependsOn;

  Task._();

  factory Task([void updates(TaskBuilder b)]) = _$Task;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(TaskBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<Task> get serializer => _$TaskSerializer();
}

class _$TaskSerializer implements PrimitiveSerializer<Task> {
  @override
  final Iterable<Type> types = const [Task, _$Task];

  @override
  final String wireName = r'Task';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    Task object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'project_id';
    yield serializers.serialize(
      object.projectId,
      specifiedType: const FullType(String),
    );
    yield r'title';
    yield serializers.serialize(
      object.title,
      specifiedType: const FullType(String),
    );
    yield r'description';
    yield serializers.serialize(
      object.description,
      specifiedType: const FullType(String),
    );
    yield r'acceptance_criteria';
    yield serializers.serialize(
      object.acceptanceCriteria,
      specifiedType: const FullType(BuiltList, [FullType(String)]),
    );
    yield r'target_scope';
    yield serializers.serialize(
      object.targetScope,
      specifiedType: const FullType(BuiltList, [FullType(String)]),
    );
    yield r'test_command';
    yield serializers.serialize(
      object.testCommand,
      specifiedType: const FullType(String),
    );
    yield r'priority';
    yield serializers.serialize(
      object.priority,
      specifiedType: const FullType(PriorityEnum),
    );
    yield r'state';
    yield serializers.serialize(
      object.state,
      specifiedType: const FullType(StateEnum),
    );
    yield r'version';
    yield serializers.serialize(
      object.version,
      specifiedType: const FullType(int),
    );
    yield r'worker_agent_id';
    yield object.workerAgentId == null
        ? null
        : serializers.serialize(
            object.workerAgentId,
            specifiedType: const FullType.nullable(String),
          );
    yield r'worker_session_id';
    yield object.workerSessionId == null
        ? null
        : serializers.serialize(
            object.workerSessionId,
            specifiedType: const FullType.nullable(String),
          );
    yield r'claimed_role';
    yield object.claimedRole == null
        ? null
        : serializers.serialize(
            object.claimedRole,
            specifiedType: const FullType.nullable(String),
          );
    yield r'lease_acquired_at';
    yield object.leaseAcquiredAt == null
        ? null
        : serializers.serialize(
            object.leaseAcquiredAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'lease_expires_at';
    yield object.leaseExpiresAt == null
        ? null
        : serializers.serialize(
            object.leaseExpiresAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'last_checkpoint_at';
    yield object.lastCheckpointAt == null
        ? null
        : serializers.serialize(
            object.lastCheckpointAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'failure_retry_count';
    yield serializers.serialize(
      object.failureRetryCount,
      specifiedType: const FullType(int),
    );
    yield r'attempt_number';
    yield serializers.serialize(
      object.attemptNumber,
      specifiedType: const FullType(int),
    );
    yield r'audit_required';
    yield serializers.serialize(
      object.auditRequired,
      specifiedType: const FullType(bool),
    );
    yield r'review_reason';
    yield object.reviewReason == null
        ? null
        : serializers.serialize(
            object.reviewReason,
            specifiedType: const FullType.nullable(String),
          );
    yield r'latest_feedback';
    yield serializers.serialize(
      object.latestFeedback,
      specifiedType: const FullType(String),
    );
    yield r'merge_status';
    yield serializers.serialize(
      object.mergeStatus,
      specifiedType: const FullType(String),
    );
    yield r'archived_at';
    yield object.archivedAt == null
        ? null
        : serializers.serialize(
            object.archivedAt,
            specifiedType: const FullType.nullable(DateTime),
          );
    yield r'created_by';
    yield object.createdBy == null
        ? null
        : serializers.serialize(
            object.createdBy,
            specifiedType: const FullType.nullable(String),
          );
    yield r'created_at';
    yield serializers.serialize(
      object.createdAt,
      specifiedType: const FullType(DateTime),
    );
    yield r'updated_at';
    yield serializers.serialize(
      object.updatedAt,
      specifiedType: const FullType(DateTime),
    );
    yield r'depends_on';
    yield serializers.serialize(
      object.dependsOn,
      specifiedType: const FullType(BuiltList, [FullType(String)]),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    Task object, {
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
    required TaskBuilder result,
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
        case r'project_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.projectId = valueDes;
          break;
        case r'title':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.title = valueDes;
          break;
        case r'description':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.description = valueDes;
          break;
        case r'acceptance_criteria':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(BuiltList, [FullType(String)]),
          ) as BuiltList<String>;
          result.acceptanceCriteria.replace(valueDes);
          break;
        case r'target_scope':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(BuiltList, [FullType(String)]),
          ) as BuiltList<String>;
          result.targetScope.replace(valueDes);
          break;
        case r'test_command':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.testCommand = valueDes;
          break;
        case r'priority':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(PriorityEnum),
          ) as PriorityEnum;
          result.priority = valueDes;
          break;
        case r'state':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(StateEnum),
          ) as StateEnum;
          result.state = valueDes;
          break;
        case r'version':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.version = valueDes;
          break;
        case r'worker_agent_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.workerAgentId = valueDes;
          break;
        case r'worker_session_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.workerSessionId = valueDes;
          break;
        case r'claimed_role':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.claimedRole = valueDes;
          break;
        case r'lease_acquired_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.leaseAcquiredAt = valueDes;
          break;
        case r'lease_expires_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.leaseExpiresAt = valueDes;
          break;
        case r'last_checkpoint_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.lastCheckpointAt = valueDes;
          break;
        case r'failure_retry_count':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.failureRetryCount = valueDes;
          break;
        case r'attempt_number':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.attemptNumber = valueDes;
          break;
        case r'audit_required':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.auditRequired = valueDes;
          break;
        case r'review_reason':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.reviewReason = valueDes;
          break;
        case r'latest_feedback':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.latestFeedback = valueDes;
          break;
        case r'merge_status':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.mergeStatus = valueDes;
          break;
        case r'archived_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(DateTime),
          ) as DateTime?;
          if (valueDes == null) continue;
          result.archivedAt = valueDes;
          break;
        case r'created_by':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.createdBy = valueDes;
          break;
        case r'created_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.createdAt = valueDes;
          break;
        case r'updated_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.updatedAt = valueDes;
          break;
        case r'depends_on':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(BuiltList, [FullType(String)]),
          ) as BuiltList<String>;
          result.dependsOn.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  Task deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = TaskBuilder();
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
