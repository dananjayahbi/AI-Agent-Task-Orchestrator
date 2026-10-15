//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters

import 'package:one_of_serializer/any_of_serializer.dart';
import 'package:one_of_serializer/one_of_serializer.dart';
import 'package:built_collection/built_collection.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/serializer.dart';
import 'package:built_value/standard_json_plugin.dart';
import 'package:built_value/iso_8601_date_time_serializer.dart';
import 'package:orchestrator_mobile/src/date_serializer.dart';
import 'package:orchestrator_mobile/src/model/date.dart';

import 'package:orchestrator_mobile/src/model/active_status_enum.dart';
import 'package:orchestrator_mobile/src/model/agent_hints.dart';
import 'package:orchestrator_mobile/src/model/agent_session.dart';
import 'package:orchestrator_mobile/src/model/agent_session_create.dart';
import 'package:orchestrator_mobile/src/model/agent_token_issue_request.dart';
import 'package:orchestrator_mobile/src/model/agent_token_issue_response.dart';
import 'package:orchestrator_mobile/src/model/alert_state.dart';
import 'package:orchestrator_mobile/src/model/attachment.dart';
import 'package:orchestrator_mobile/src/model/attachment_content.dart';
import 'package:orchestrator_mobile/src/model/attachment_delete.dart';
import 'package:orchestrator_mobile/src/model/attachment_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/audit_decision.dart';
import 'package:orchestrator_mobile/src/model/audit_report.dart';
import 'package:orchestrator_mobile/src/model/audit_report_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/audit_verdict_request.dart';
import 'package:orchestrator_mobile/src/model/audit_verdict_response.dart';
import 'package:orchestrator_mobile/src/model/capability_enum.dart';
import 'package:orchestrator_mobile/src/model/checkpoint.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_create.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_create_kind_enum.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_write_response.dart';
import 'package:orchestrator_mobile/src/model/claim_request.dart';
import 'package:orchestrator_mobile/src/model/claim_response.dart';
import 'package:orchestrator_mobile/src/model/code_enum.dart';
import 'package:orchestrator_mobile/src/model/dashboard_summary.dart';
import 'package:orchestrator_mobile/src/model/decided_via_enum.dart';
import 'package:orchestrator_mobile/src/model/decision_enum.dart';
import 'package:orchestrator_mobile/src/model/device_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/device_register_request.dart';
import 'package:orchestrator_mobile/src/model/device_register_response.dart';
import 'package:orchestrator_mobile/src/model/device_summary.dart';
import 'package:orchestrator_mobile/src/model/error_envelope.dart';
import 'package:orchestrator_mobile/src/model/error_envelope_body.dart';
import 'package:orchestrator_mobile/src/model/event_actor.dart';
import 'package:orchestrator_mobile/src/model/event_actor_type_enum.dart';
import 'package:orchestrator_mobile/src/model/event_envelope.dart';
import 'package:orchestrator_mobile/src/model/event_envelope_type_enum.dart';
import 'package:orchestrator_mobile/src/model/event_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/event_type_enum.dart';
import 'package:orchestrator_mobile/src/model/health_live.dart';
import 'package:orchestrator_mobile/src/model/health_ready.dart';
import 'package:orchestrator_mobile/src/model/kind_e0d_enum.dart';
import 'package:orchestrator_mobile/src/model/lease_extension_mode_enum.dart';
import 'package:orchestrator_mobile/src/model/lease_record.dart';
import 'package:orchestrator_mobile/src/model/login_request.dart';
import 'package:orchestrator_mobile/src/model/merge_queue_item.dart';
import 'package:orchestrator_mobile/src/model/merge_queue_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/merge_result_request.dart';
import 'package:orchestrator_mobile/src/model/merge_result_response.dart';
import 'package:orchestrator_mobile/src/model/merge_start_request.dart';
import 'package:orchestrator_mobile/src/model/merge_start_response.dart';
import 'package:orchestrator_mobile/src/model/merge_strategy_enum.dart';
import 'package:orchestrator_mobile/src/model/notification_preference.dart';
import 'package:orchestrator_mobile/src/model/notification_preferences_request.dart';
import 'package:orchestrator_mobile/src/model/notification_preferences_response.dart';
import 'package:orchestrator_mobile/src/model/ops_health.dart';
import 'package:orchestrator_mobile/src/model/ops_overview.dart';
import 'package:orchestrator_mobile/src/model/orchestrator_manifest.dart';
import 'package:orchestrator_mobile/src/model/owner_session.dart';
import 'package:orchestrator_mobile/src/model/patched_project_policy.dart';
import 'package:orchestrator_mobile/src/model/patched_project_update.dart';
import 'package:orchestrator_mobile/src/model/patched_task_update.dart';
import 'package:orchestrator_mobile/src/model/platform_enum.dart';
import 'package:orchestrator_mobile/src/model/policy_decision_enum.dart';
import 'package:orchestrator_mobile/src/model/policy_preset_enum.dart';
import 'package:orchestrator_mobile/src/model/priority_enum.dart';
import 'package:orchestrator_mobile/src/model/project.dart';
import 'package:orchestrator_mobile/src/model/project_create.dart';
import 'package:orchestrator_mobile/src/model/project_dashboard_card.dart';
import 'package:orchestrator_mobile/src/model/project_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/project_policy.dart';
import 'package:orchestrator_mobile/src/model/proposed_verdict_enum.dart';
import 'package:orchestrator_mobile/src/model/queue_task_state.dart';
import 'package:orchestrator_mobile/src/model/refreshed.dart';
import 'package:orchestrator_mobile/src/model/release_request.dart';
import 'package:orchestrator_mobile/src/model/resolution.dart';
import 'package:orchestrator_mobile/src/model/resolution_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/resolution_patch.dart';
import 'package:orchestrator_mobile/src/model/resolution_submit.dart';
import 'package:orchestrator_mobile/src/model/resolution_task_state.dart';
import 'package:orchestrator_mobile/src/model/resolution_write_response.dart';
import 'package:orchestrator_mobile/src/model/result_enum.dart';
import 'package:orchestrator_mobile/src/model/review_decision_record.dart';
import 'package:orchestrator_mobile/src/model/review_decision_request.dart';
import 'package:orchestrator_mobile/src/model/review_decision_response.dart';
import 'package:orchestrator_mobile/src/model/revoked.dart';
import 'package:orchestrator_mobile/src/model/role_enum.dart';
import 'package:orchestrator_mobile/src/model/rules_block.dart';
import 'package:orchestrator_mobile/src/model/state_counts.dart';
import 'package:orchestrator_mobile/src/model/state_enum.dart';
import 'package:orchestrator_mobile/src/model/task.dart';
import 'package:orchestrator_mobile/src/model/task_create.dart';
import 'package:orchestrator_mobile/src/model/task_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/token_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/token_summary.dart';
import 'package:orchestrator_mobile/src/model/transport_enum.dart';
import 'package:orchestrator_mobile/src/model/user_summary.dart';
import 'package:orchestrator_mobile/src/model/verdict_enum.dart';
import 'package:orchestrator_mobile/src/model/verdict_task_state.dart';

part 'serializers.g.dart';

@SerializersFor([
  ActiveStatusEnum,
  AgentHints,
  AgentSession,
  AgentSessionCreate,
  AgentTokenIssueRequest,
  AgentTokenIssueResponse,
  AlertState,
  Attachment,
  AttachmentContent,
  AttachmentDelete,
  AttachmentListEnvelope,
  AuditDecision,
  AuditReport,
  AuditReportListEnvelope,
  AuditVerdictRequest,
  AuditVerdictResponse,
  CapabilityEnum,
  Checkpoint,
  CheckpointCreate,
  CheckpointCreateKindEnum,
  CheckpointListEnvelope,
  CheckpointWriteResponse,
  ClaimRequest,
  ClaimResponse,
  CodeEnum,
  DashboardSummary,
  DecidedViaEnum,
  DecisionEnum,
  DeviceListEnvelope,
  DeviceRegisterRequest,
  DeviceRegisterResponse,
  DeviceSummary,
  ErrorEnvelope,
  ErrorEnvelopeBody,
  EventActor,
  EventActorTypeEnum,
  EventEnvelope,
  EventEnvelopeTypeEnum,
  EventListEnvelope,
  EventTypeEnum,
  HealthLive,
  HealthReady,
  KindE0dEnum,
  LeaseExtensionModeEnum,
  LeaseRecord,
  LoginRequest,
  MergeQueueItem,
  MergeQueueListEnvelope,
  MergeResultRequest,
  MergeResultResponse,
  MergeStartRequest,
  MergeStartResponse,
  MergeStrategyEnum,
  NotificationPreference,
  NotificationPreferencesRequest,
  NotificationPreferencesResponse,
  OpsHealth,
  OpsOverview,
  OrchestratorManifest,
  OwnerSession,
  PatchedProjectPolicy,
  PatchedProjectUpdate,
  PatchedTaskUpdate,
  PlatformEnum,
  PolicyDecisionEnum,
  PolicyPresetEnum,
  PriorityEnum,
  Project,
  ProjectCreate,
  ProjectDashboardCard,
  ProjectListEnvelope,
  ProjectPolicy,
  ProposedVerdictEnum,
  QueueTaskState,
  Refreshed,
  ReleaseRequest,
  Resolution,
  ResolutionListEnvelope,
  ResolutionPatch,
  ResolutionSubmit,
  ResolutionTaskState,
  ResolutionWriteResponse,
  ResultEnum,
  ReviewDecisionRecord,
  ReviewDecisionRequest,
  ReviewDecisionResponse,
  Revoked,
  RoleEnum,
  RulesBlock,
  StateCounts,
  StateEnum,
  Task,
  TaskCreate,
  TaskListEnvelope,
  TokenListEnvelope,
  TokenSummary,
  TransportEnum,
  UserSummary,
  VerdictEnum,
  VerdictTaskState,
])
Serializers serializers = (_$serializers.toBuilder()
      ..addBuilderFactory(
        const FullType(BuiltMap, [FullType(String), FullType(String)]),
        () => MapBuilder<String, String>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(TokenSummary)]),
        () => ListBuilder<TokenSummary>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(NotificationPreference)]),
        () => ListBuilder<NotificationPreference>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(AuditReport)]),
        () => ListBuilder<AuditReport>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(ProjectDashboardCard)]),
        () => ListBuilder<ProjectDashboardCard>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [
          FullType(BuiltMap, [FullType(String), FullType(JsonObject)])
        ]),
        () => ListBuilder<BuiltMap<String, JsonObject>>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(EventEnvelope)]),
        () => ListBuilder<EventEnvelope>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(Resolution)]),
        () => ListBuilder<Resolution>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(Checkpoint)]),
        () => ListBuilder<Checkpoint>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(AlertState)]),
        () => ListBuilder<AlertState>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(Project)]),
        () => ListBuilder<Project>(),
      )
      ..addBuilderFactory(
        const FullType(
            BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
        () => MapBuilder<String, JsonObject?>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(MergeQueueItem)]),
        () => ListBuilder<MergeQueueItem>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(Attachment)]),
        () => ListBuilder<Attachment>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(Task)]),
        () => ListBuilder<Task>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(String)]),
        () => ListBuilder<String>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(DeviceSummary)]),
        () => ListBuilder<DeviceSummary>(),
      )
      ..add(const OneOfSerializer())
      ..add(const AnyOfSerializer())
      ..add(const DateSerializer())
      ..add(Iso8601DateTimeSerializer()))
    .build();

Serializers standardSerializers =
    (serializers.toBuilder()..addPlugin(StandardJsonPlugin())).build();
