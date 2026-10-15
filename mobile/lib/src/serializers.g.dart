// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'serializers.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

Serializers _$serializers = (Serializers().toBuilder()
      ..add(ActiveStatusEnum.serializer)
      ..add(AgentHints.serializer)
      ..add(AgentSession.serializer)
      ..add(AgentSessionCreate.serializer)
      ..add(AgentTokenIssueRequest.serializer)
      ..add(AgentTokenIssueResponse.serializer)
      ..add(AlertState.serializer)
      ..add(Attachment.serializer)
      ..add(AttachmentContent.serializer)
      ..add(AttachmentDelete.serializer)
      ..add(AttachmentListEnvelope.serializer)
      ..add(AuditDecision.serializer)
      ..add(AuditReport.serializer)
      ..add(AuditReportListEnvelope.serializer)
      ..add(AuditVerdictRequest.serializer)
      ..add(AuditVerdictResponse.serializer)
      ..add(CapabilityEnum.serializer)
      ..add(Checkpoint.serializer)
      ..add(CheckpointCreate.serializer)
      ..add(CheckpointCreateKindEnum.serializer)
      ..add(CheckpointListEnvelope.serializer)
      ..add(CheckpointWriteResponse.serializer)
      ..add(ClaimRequest.serializer)
      ..add(ClaimResponse.serializer)
      ..add(CodeEnum.serializer)
      ..add(DashboardSummary.serializer)
      ..add(DecidedViaEnum.serializer)
      ..add(DecisionEnum.serializer)
      ..add(DeviceListEnvelope.serializer)
      ..add(DeviceRegisterRequest.serializer)
      ..add(DeviceRegisterResponse.serializer)
      ..add(DeviceSummary.serializer)
      ..add(ErrorEnvelope.serializer)
      ..add(ErrorEnvelopeBody.serializer)
      ..add(EventActor.serializer)
      ..add(EventActorTypeEnum.serializer)
      ..add(EventEnvelope.serializer)
      ..add(EventEnvelopeTypeEnum.serializer)
      ..add(EventListEnvelope.serializer)
      ..add(HealthLive.serializer)
      ..add(HealthReady.serializer)
      ..add(KindE0dEnum.serializer)
      ..add(LeaseExtensionModeEnum.serializer)
      ..add(LeaseRecord.serializer)
      ..add(LoginRequest.serializer)
      ..add(MergeQueueItem.serializer)
      ..add(MergeQueueListEnvelope.serializer)
      ..add(MergeResultRequest.serializer)
      ..add(MergeResultResponse.serializer)
      ..add(MergeStartRequest.serializer)
      ..add(MergeStartResponse.serializer)
      ..add(MergeStrategyEnum.serializer)
      ..add(OpsHealth.serializer)
      ..add(OpsOverview.serializer)
      ..add(OrchestratorManifest.serializer)
      ..add(OwnerSession.serializer)
      ..add(PatchedProjectPolicy.serializer)
      ..add(PatchedProjectUpdate.serializer)
      ..add(PatchedTaskUpdate.serializer)
      ..add(PlatformEnum.serializer)
      ..add(PolicyDecisionEnum.serializer)
      ..add(PolicyPresetEnum.serializer)
      ..add(PriorityEnum.serializer)
      ..add(Project.serializer)
      ..add(ProjectCreate.serializer)
      ..add(ProjectDashboardCard.serializer)
      ..add(ProjectListEnvelope.serializer)
      ..add(ProjectPolicy.serializer)
      ..add(ProposedVerdictEnum.serializer)
      ..add(QueueTaskState.serializer)
      ..add(Refreshed.serializer)
      ..add(ReleaseRequest.serializer)
      ..add(Resolution.serializer)
      ..add(ResolutionListEnvelope.serializer)
      ..add(ResolutionPatch.serializer)
      ..add(ResolutionSubmit.serializer)
      ..add(ResolutionTaskState.serializer)
      ..add(ResolutionWriteResponse.serializer)
      ..add(ResultEnum.serializer)
      ..add(ReviewDecisionRecord.serializer)
      ..add(ReviewDecisionRequest.serializer)
      ..add(ReviewDecisionResponse.serializer)
      ..add(Revoked.serializer)
      ..add(RoleEnum.serializer)
      ..add(RulesBlock.serializer)
      ..add(StateCounts.serializer)
      ..add(StateEnum.serializer)
      ..add(Task.serializer)
      ..add(TaskCreate.serializer)
      ..add(TaskListEnvelope.serializer)
      ..add(TokenListEnvelope.serializer)
      ..add(TokenSummary.serializer)
      ..add(TransportEnum.serializer)
      ..add(UserSummary.serializer)
      ..add(VerdictEnum.serializer)
      ..add(VerdictTaskState.serializer)
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(Attachment)]),
          () => ListBuilder<Attachment>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(AuditReport)]),
          () => ListBuilder<AuditReport>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [
            const FullType(BuiltMap, const [
              const FullType(String),
              const FullType.nullable(JsonObject)
            ])
          ]),
          () => ListBuilder<BuiltMap<String, JsonObject?>>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(Checkpoint)]),
          () => ListBuilder<Checkpoint>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(DeviceSummary)]),
          () => ListBuilder<DeviceSummary>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(EventEnvelope)]),
          () => ListBuilder<EventEnvelope>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(MergeQueueItem)]),
          () => ListBuilder<MergeQueueItem>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(Project)]),
          () => ListBuilder<Project>())
      ..addBuilderFactory(
          const FullType(
              BuiltList, const [const FullType(ProjectDashboardCard)]),
          () => ListBuilder<ProjectDashboardCard>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(Resolution)]),
          () => ListBuilder<Resolution>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(Attachment)]),
          () => ListBuilder<Attachment>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(String)]),
          () => ListBuilder<String>())
      ..addBuilderFactory(
          const FullType(BuiltMap, const [
            const FullType(String),
            const FullType.nullable(JsonObject)
          ]),
          () => MapBuilder<String, JsonObject?>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(Task)]),
          () => ListBuilder<Task>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(TokenSummary)]),
          () => ListBuilder<TokenSummary>())
      ..addBuilderFactory(
          const FullType(
              BuiltMap, const [const FullType(String), const FullType(String)]),
          () => MapBuilder<String, String>())
      ..addBuilderFactory(
          const FullType(
              BuiltMap, const [const FullType(String), const FullType(String)]),
          () => MapBuilder<String, String>())
      ..addBuilderFactory(
          const FullType(BuiltMap, const [
            const FullType(String),
            const FullType.nullable(JsonObject)
          ]),
          () => MapBuilder<String, JsonObject?>())
      ..addBuilderFactory(
          const FullType(BuiltMap, const [
            const FullType(String),
            const FullType.nullable(JsonObject)
          ]),
          () => MapBuilder<String, JsonObject?>())
      ..addBuilderFactory(
          const FullType(BuiltList, const [const FullType(AlertState)]),
          () => ListBuilder<AlertState>())
      ..addBuilderFactory(
          const FullType(BuiltMap, const [
            const FullType(String),
            const FullType.nullable(JsonObject)
          ]),
          () => MapBuilder<String, JsonObject?>())
      ..addBuilderFactory(
          const FullType(BuiltMap, const [
            const FullType(String),
            const FullType.nullable(JsonObject)
          ]),
          () => MapBuilder<String, JsonObject?>()))
    .build();

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
