//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/project_dashboard_card.dart';
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'dashboard_summary.g.dart';

/// ``GET /dashboard/summary`` body — one card per registered project.
///
/// Properties:
/// * [projects] - Every registered project, ordered by project id; empty when no projects exist. Single-resource GET — no cursor pagination (pagination.md).
@BuiltValue()
abstract class DashboardSummary
    implements Built<DashboardSummary, DashboardSummaryBuilder> {
  /// Every registered project, ordered by project id; empty when no projects exist. Single-resource GET — no cursor pagination (pagination.md).
  @BuiltValueField(wireName: r'projects')
  BuiltList<ProjectDashboardCard> get projects;

  DashboardSummary._();

  factory DashboardSummary([void updates(DashboardSummaryBuilder b)]) =
      _$DashboardSummary;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(DashboardSummaryBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<DashboardSummary> get serializer =>
      _$DashboardSummarySerializer();
}

class _$DashboardSummarySerializer
    implements PrimitiveSerializer<DashboardSummary> {
  @override
  final Iterable<Type> types = const [DashboardSummary, _$DashboardSummary];

  @override
  final String wireName = r'DashboardSummary';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    DashboardSummary object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'projects';
    yield serializers.serialize(
      object.projects,
      specifiedType:
          const FullType(BuiltList, [FullType(ProjectDashboardCard)]),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    DashboardSummary object, {
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
    required DashboardSummaryBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'projects':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType(BuiltList, [FullType(ProjectDashboardCard)]),
          ) as BuiltList<ProjectDashboardCard>;
          result.projects.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  DashboardSummary deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = DashboardSummaryBuilder();
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
