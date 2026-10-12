//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'event_envelope_type_enum.g.dart';

/// * `project.created` - project.created * `project.updated` - project.updated * `task.created` - task.created * `task.updated` - task.updated * `task.transitioned` - task.transitioned * `task.claimed` - task.claimed * `task.released` - task.released * `task.checkpoint` - task.checkpoint * `task.lease_expiring` - task.lease_expiring * `task.lease_expired` - task.lease_expired * `attachment.processing` - attachment.processing * `attachment.ready` - attachment.ready * `attachment.failed` - attachment.failed * `audit.claimed` - audit.claimed * `audit.passed` - audit.passed * `audit.escalated` - audit.escalated * `review.requested` - review.requested * `review.decided` - review.decided * `merge.started` - merge.started * `merge.succeeded` - merge.succeeded * `merge.failed` - merge.failed * `agent.session_started` - agent.session_started * `agent.session_ended` - agent.session_ended * `system.alert` - system.alert
class EventEnvelopeTypeEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'project.created')
  static const EventEnvelopeTypeEnum projectPeriodCreated =
      _$projectPeriodCreated;
  @BuiltValueEnumConst(wireName: r'project.updated')
  static const EventEnvelopeTypeEnum projectPeriodUpdated =
      _$projectPeriodUpdated;
  @BuiltValueEnumConst(wireName: r'task.created')
  static const EventEnvelopeTypeEnum taskPeriodCreated = _$taskPeriodCreated;
  @BuiltValueEnumConst(wireName: r'task.updated')
  static const EventEnvelopeTypeEnum taskPeriodUpdated = _$taskPeriodUpdated;
  @BuiltValueEnumConst(wireName: r'task.transitioned')
  static const EventEnvelopeTypeEnum taskPeriodTransitioned =
      _$taskPeriodTransitioned;
  @BuiltValueEnumConst(wireName: r'task.claimed')
  static const EventEnvelopeTypeEnum taskPeriodClaimed = _$taskPeriodClaimed;
  @BuiltValueEnumConst(wireName: r'task.released')
  static const EventEnvelopeTypeEnum taskPeriodReleased = _$taskPeriodReleased;
  @BuiltValueEnumConst(wireName: r'task.checkpoint')
  static const EventEnvelopeTypeEnum taskPeriodCheckpoint =
      _$taskPeriodCheckpoint;
  @BuiltValueEnumConst(wireName: r'task.lease_expiring')
  static const EventEnvelopeTypeEnum taskPeriodLeaseExpiring =
      _$taskPeriodLeaseExpiring;
  @BuiltValueEnumConst(wireName: r'task.lease_expired')
  static const EventEnvelopeTypeEnum taskPeriodLeaseExpired =
      _$taskPeriodLeaseExpired;
  @BuiltValueEnumConst(wireName: r'attachment.processing')
  static const EventEnvelopeTypeEnum attachmentPeriodProcessing =
      _$attachmentPeriodProcessing;
  @BuiltValueEnumConst(wireName: r'attachment.ready')
  static const EventEnvelopeTypeEnum attachmentPeriodReady =
      _$attachmentPeriodReady;
  @BuiltValueEnumConst(wireName: r'attachment.failed')
  static const EventEnvelopeTypeEnum attachmentPeriodFailed =
      _$attachmentPeriodFailed;
  @BuiltValueEnumConst(wireName: r'audit.claimed')
  static const EventEnvelopeTypeEnum auditPeriodClaimed = _$auditPeriodClaimed;
  @BuiltValueEnumConst(wireName: r'audit.passed')
  static const EventEnvelopeTypeEnum auditPeriodPassed = _$auditPeriodPassed;
  @BuiltValueEnumConst(wireName: r'audit.escalated')
  static const EventEnvelopeTypeEnum auditPeriodEscalated =
      _$auditPeriodEscalated;
  @BuiltValueEnumConst(wireName: r'review.requested')
  static const EventEnvelopeTypeEnum reviewPeriodRequested =
      _$reviewPeriodRequested;
  @BuiltValueEnumConst(wireName: r'review.decided')
  static const EventEnvelopeTypeEnum reviewPeriodDecided =
      _$reviewPeriodDecided;
  @BuiltValueEnumConst(wireName: r'merge.started')
  static const EventEnvelopeTypeEnum mergePeriodStarted = _$mergePeriodStarted;
  @BuiltValueEnumConst(wireName: r'merge.succeeded')
  static const EventEnvelopeTypeEnum mergePeriodSucceeded =
      _$mergePeriodSucceeded;
  @BuiltValueEnumConst(wireName: r'merge.failed')
  static const EventEnvelopeTypeEnum mergePeriodFailed = _$mergePeriodFailed;
  @BuiltValueEnumConst(wireName: r'agent.session_started')
  static const EventEnvelopeTypeEnum agentPeriodSessionStarted =
      _$agentPeriodSessionStarted;
  @BuiltValueEnumConst(wireName: r'agent.session_ended')
  static const EventEnvelopeTypeEnum agentPeriodSessionEnded =
      _$agentPeriodSessionEnded;
  @BuiltValueEnumConst(wireName: r'system.alert')
  static const EventEnvelopeTypeEnum systemPeriodAlert = _$systemPeriodAlert;

  static Serializer<EventEnvelopeTypeEnum> get serializer =>
      _$eventEnvelopeTypeEnumSerializer;

  const EventEnvelopeTypeEnum._(String name) : super(name);

  static BuiltSet<EventEnvelopeTypeEnum> get values => _$values;
  static EventEnvelopeTypeEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class EventEnvelopeTypeEnumMixin = Object
    with _$EventEnvelopeTypeEnumMixin;
