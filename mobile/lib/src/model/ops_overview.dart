//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/alert_state.dart';
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/ops_health.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'ops_overview.g.dart';

/// ``GET /api/v1/ops/overview`` body — one snapshot for the ops view.
///
/// Properties:
/// * [schemaVersion] - Payload contract version; bump on breaking shape changes.
/// * [generatedAt] - ISO timestamp of this snapshot — the view shows it as data freshness so a frozen view is recognizable as stale (MT-6.4-03 risk note; polling is the recorded update mode).
/// * [metrics] - MT-6.4-01's nine Section 17 metrics plus heartbeats, verbatim from the /metrics collector (docs/plan/metrics.md is the semantics table; this payload and /metrics cannot disagree — same collect()).
/// * [alerts] - MT-6.4-02's six Section 17 rules in plan order, with firing state and context (docs/plan/alerts.md).
/// * [health] - Section 17 Health row — live/ready plus heartbeat visibility via metrics.
@BuiltValue()
abstract class OpsOverview implements Built<OpsOverview, OpsOverviewBuilder> {
  /// Payload contract version; bump on breaking shape changes.
  @BuiltValueField(wireName: r'schema_version')
  String get schemaVersion;

  /// ISO timestamp of this snapshot — the view shows it as data freshness so a frozen view is recognizable as stale (MT-6.4-03 risk note; polling is the recorded update mode).
  @BuiltValueField(wireName: r'generated_at')
  String get generatedAt;

  /// MT-6.4-01's nine Section 17 metrics plus heartbeats, verbatim from the /metrics collector (docs/plan/metrics.md is the semantics table; this payload and /metrics cannot disagree — same collect()).
  @BuiltValueField(wireName: r'metrics')
  BuiltMap<String, JsonObject?> get metrics;

  /// MT-6.4-02's six Section 17 rules in plan order, with firing state and context (docs/plan/alerts.md).
  @BuiltValueField(wireName: r'alerts')
  BuiltList<AlertState> get alerts;

  /// Section 17 Health row — live/ready plus heartbeat visibility via metrics.
  @BuiltValueField(wireName: r'health')
  OpsHealth get health;

  OpsOverview._();

  factory OpsOverview([void updates(OpsOverviewBuilder b)]) = _$OpsOverview;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(OpsOverviewBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<OpsOverview> get serializer => _$OpsOverviewSerializer();
}

class _$OpsOverviewSerializer implements PrimitiveSerializer<OpsOverview> {
  @override
  final Iterable<Type> types = const [OpsOverview, _$OpsOverview];

  @override
  final String wireName = r'OpsOverview';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    OpsOverview object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'schema_version';
    yield serializers.serialize(
      object.schemaVersion,
      specifiedType: const FullType(String),
    );
    yield r'generated_at';
    yield serializers.serialize(
      object.generatedAt,
      specifiedType: const FullType(String),
    );
    yield r'metrics';
    yield serializers.serialize(
      object.metrics,
      specifiedType: const FullType(
          BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
    );
    yield r'alerts';
    yield serializers.serialize(
      object.alerts,
      specifiedType: const FullType(BuiltList, [FullType(AlertState)]),
    );
    yield r'health';
    yield serializers.serialize(
      object.health,
      specifiedType: const FullType(OpsHealth),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    OpsOverview object, {
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
    required OpsOverviewBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'schema_version':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.schemaVersion = valueDes;
          break;
        case r'generated_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.generatedAt = valueDes;
          break;
        case r'metrics':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(
                BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
          ) as BuiltMap<String, JsonObject?>;
          result.metrics.replace(valueDes);
          break;
        case r'alerts':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(BuiltList, [FullType(AlertState)]),
          ) as BuiltList<AlertState>;
          result.alerts.replace(valueDes);
          break;
        case r'health':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(OpsHealth),
          ) as OpsHealth;
          result.health.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  OpsOverview deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = OpsOverviewBuilder();
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
