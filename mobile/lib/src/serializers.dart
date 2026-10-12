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
import 'package:orchestrator_mobile/src/model/agent_token_issue_request.dart';
import 'package:orchestrator_mobile/src/model/agent_token_issue_response.dart';
import 'package:orchestrator_mobile/src/model/code_enum.dart';
import 'package:orchestrator_mobile/src/model/device_register_request.dart';
import 'package:orchestrator_mobile/src/model/device_register_response.dart';
import 'package:orchestrator_mobile/src/model/error_envelope.dart';
import 'package:orchestrator_mobile/src/model/health_live.dart';
import 'package:orchestrator_mobile/src/model/health_ready.dart';
import 'package:orchestrator_mobile/src/model/kind_enum.dart';
import 'package:orchestrator_mobile/src/model/lease_extension_mode_enum.dart';
import 'package:orchestrator_mobile/src/model/login_request.dart';
import 'package:orchestrator_mobile/src/model/merge_strategy_enum.dart';
import 'package:orchestrator_mobile/src/model/orchestrator_manifest.dart';
import 'package:orchestrator_mobile/src/model/owner_session.dart';
import 'package:orchestrator_mobile/src/model/patched_project_policy.dart';
import 'package:orchestrator_mobile/src/model/patched_project_update.dart';
import 'package:orchestrator_mobile/src/model/patched_task_update.dart';
import 'package:orchestrator_mobile/src/model/platform_enum.dart';
import 'package:orchestrator_mobile/src/model/priority_enum.dart';
import 'package:orchestrator_mobile/src/model/project.dart';
import 'package:orchestrator_mobile/src/model/project_create.dart';
import 'package:orchestrator_mobile/src/model/project_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/project_policy.dart';
import 'package:orchestrator_mobile/src/model/refreshed.dart';
import 'package:orchestrator_mobile/src/model/revoked.dart';
import 'package:orchestrator_mobile/src/model/state_enum.dart';
import 'package:orchestrator_mobile/src/model/task.dart';
import 'package:orchestrator_mobile/src/model/task_create.dart';
import 'package:orchestrator_mobile/src/model/task_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/token_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/token_summary.dart';
import 'package:orchestrator_mobile/src/model/user_summary.dart';

part 'serializers.g.dart';

@SerializersFor([
  ActiveStatusEnum,
  AgentHints,
  AgentTokenIssueRequest,
  AgentTokenIssueResponse,
  CodeEnum,
  DeviceRegisterRequest,
  DeviceRegisterResponse,
  ErrorEnvelope,
  HealthLive,
  HealthReady,
  KindEnum,
  LeaseExtensionModeEnum,
  LoginRequest,
  MergeStrategyEnum,
  OrchestratorManifest,
  OwnerSession,
  PatchedProjectPolicy,
  PatchedProjectUpdate,
  PatchedTaskUpdate,
  PlatformEnum,
  PriorityEnum,
  Project,
  ProjectCreate,
  ProjectListEnvelope,
  ProjectPolicy,
  Refreshed,
  Revoked,
  StateEnum,
  Task,
  TaskCreate,
  TaskListEnvelope,
  TokenListEnvelope,
  TokenSummary,
  UserSummary,
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
        const FullType(BuiltList, [FullType(Project)]),
        () => ListBuilder<Project>(),
      )
      ..addBuilderFactory(
        const FullType(
            BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
        () => MapBuilder<String, JsonObject?>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(Task)]),
        () => ListBuilder<Task>(),
      )
      ..addBuilderFactory(
        const FullType(BuiltList, [FullType(String)]),
        () => ListBuilder<String>(),
      )
      ..add(const OneOfSerializer())
      ..add(const AnyOfSerializer())
      ..add(const DateSerializer())
      ..add(Iso8601DateTimeSerializer()))
    .build();

Serializers standardSerializers =
    (serializers.toBuilder()..addPlugin(StandardJsonPlugin())).build();
