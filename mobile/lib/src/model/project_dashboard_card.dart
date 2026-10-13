//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/state_counts.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'project_dashboard_card.g.dart';

/// One project's Overview card — Section 14.1 Home row; FR-MOB-01.
///
/// Properties:
/// * [projectId] - Canonical PID + five digits (Section 7.3), in id order.
/// * [name]
/// * [stateCounts] - Counts over the project's non-archived tasks, keyed by the six canonical G-01 states, zero-filled (ADR-010; T19 visibility).
/// * [velocity] - Tasks that reached `completed` in the trailing 7-day window (server clock, transition log). Conservative documented default — the plan states no definition (OQ); this payload is authoritative and clients never recompute it (FR-MOB-01).
/// * [activeAgents] - AgentSession rows of this project with ended_at null (Section 7.2 lifecycle; no heartbeat freshness invented).
@BuiltValue()
abstract class ProjectDashboardCard
    implements Built<ProjectDashboardCard, ProjectDashboardCardBuilder> {
  /// Canonical PID + five digits (Section 7.3), in id order.
  @BuiltValueField(wireName: r'project_id')
  String get projectId;

  @BuiltValueField(wireName: r'name')
  String get name;

  /// Counts over the project's non-archived tasks, keyed by the six canonical G-01 states, zero-filled (ADR-010; T19 visibility).
  @BuiltValueField(wireName: r'state_counts')
  StateCounts get stateCounts;

  /// Tasks that reached `completed` in the trailing 7-day window (server clock, transition log). Conservative documented default — the plan states no definition (OQ); this payload is authoritative and clients never recompute it (FR-MOB-01).
  @BuiltValueField(wireName: r'velocity')
  int get velocity;

  /// AgentSession rows of this project with ended_at null (Section 7.2 lifecycle; no heartbeat freshness invented).
  @BuiltValueField(wireName: r'active_agents')
  int get activeAgents;

  ProjectDashboardCard._();

  factory ProjectDashboardCard([void updates(ProjectDashboardCardBuilder b)]) =
      _$ProjectDashboardCard;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ProjectDashboardCardBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<ProjectDashboardCard> get serializer =>
      _$ProjectDashboardCardSerializer();
}

class _$ProjectDashboardCardSerializer
    implements PrimitiveSerializer<ProjectDashboardCard> {
  @override
  final Iterable<Type> types = const [
    ProjectDashboardCard,
    _$ProjectDashboardCard
  ];

  @override
  final String wireName = r'ProjectDashboardCard';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ProjectDashboardCard object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'project_id';
    yield serializers.serialize(
      object.projectId,
      specifiedType: const FullType(String),
    );
    yield r'name';
    yield serializers.serialize(
      object.name,
      specifiedType: const FullType(String),
    );
    yield r'state_counts';
    yield serializers.serialize(
      object.stateCounts,
      specifiedType: const FullType(StateCounts),
    );
    yield r'velocity';
    yield serializers.serialize(
      object.velocity,
      specifiedType: const FullType(int),
    );
    yield r'active_agents';
    yield serializers.serialize(
      object.activeAgents,
      specifiedType: const FullType(int),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    ProjectDashboardCard object, {
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
    required ProjectDashboardCardBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'project_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.projectId = valueDes;
          break;
        case r'name':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.name = valueDes;
          break;
        case r'state_counts':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(StateCounts),
          ) as StateCounts;
          result.stateCounts.replace(valueDes);
          break;
        case r'velocity':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.velocity = valueDes;
          break;
        case r'active_agents':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(int),
          ) as int;
          result.activeAgents = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ProjectDashboardCard deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ProjectDashboardCardBuilder();
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
