//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'alert_state.g.dart';

/// One MT-6.4-02 rule's state — field names are the alert contract.
///
/// Properties:
/// * [id] - Stable rule id: sweeper_not_running, attachment_backlog, push_failures, tunnel_down, repeated_auth_failures, media_disk_usage (Section 17 Alerts row, plan order).
/// * [name] - The Section 17 alert name, verbatim.
/// * [severity] - 'critical' or 'warning' (docs/plan/alerts.md).
/// * [firing] - True while the rule's condition holds.
/// * [status] - 'firing', 'ok', or 'unknown' (signal never reported — never fires).
/// * [since] - ISO onset of the current firing stretch, or null when resting.
/// * [signal] - Numbers only — counts, ages, rates. No identities, no secrets (12.4).
/// * [threshold] - The configurable threshold(s) in force.
/// * [runbook] - Section 17 runbook name where one exists (else null).
@BuiltValue()
abstract class AlertState implements Built<AlertState, AlertStateBuilder> {
  /// Stable rule id: sweeper_not_running, attachment_backlog, push_failures, tunnel_down, repeated_auth_failures, media_disk_usage (Section 17 Alerts row, plan order).
  @BuiltValueField(wireName: r'id')
  String get id;

  /// The Section 17 alert name, verbatim.
  @BuiltValueField(wireName: r'name')
  String get name;

  /// 'critical' or 'warning' (docs/plan/alerts.md).
  @BuiltValueField(wireName: r'severity')
  String get severity;

  /// True while the rule's condition holds.
  @BuiltValueField(wireName: r'firing')
  bool get firing;

  /// 'firing', 'ok', or 'unknown' (signal never reported — never fires).
  @BuiltValueField(wireName: r'status')
  String get status;

  /// ISO onset of the current firing stretch, or null when resting.
  @BuiltValueField(wireName: r'since')
  String? get since;

  /// Numbers only — counts, ages, rates. No identities, no secrets (12.4).
  @BuiltValueField(wireName: r'signal')
  BuiltMap<String, JsonObject?> get signal;

  /// The configurable threshold(s) in force.
  @BuiltValueField(wireName: r'threshold')
  BuiltMap<String, JsonObject?> get threshold;

  /// Section 17 runbook name where one exists (else null).
  @BuiltValueField(wireName: r'runbook')
  String? get runbook;

  AlertState._();

  factory AlertState([void updates(AlertStateBuilder b)]) = _$AlertState;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AlertStateBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AlertState> get serializer => _$AlertStateSerializer();
}

class _$AlertStateSerializer implements PrimitiveSerializer<AlertState> {
  @override
  final Iterable<Type> types = const [AlertState, _$AlertState];

  @override
  final String wireName = r'AlertState';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AlertState object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'name';
    yield serializers.serialize(
      object.name,
      specifiedType: const FullType(String),
    );
    yield r'severity';
    yield serializers.serialize(
      object.severity,
      specifiedType: const FullType(String),
    );
    yield r'firing';
    yield serializers.serialize(
      object.firing,
      specifiedType: const FullType(bool),
    );
    yield r'status';
    yield serializers.serialize(
      object.status,
      specifiedType: const FullType(String),
    );
    if (object.since != null) {
      yield r'since';
      yield serializers.serialize(
        object.since,
        specifiedType: const FullType.nullable(String),
      );
    }
    yield r'signal';
    yield serializers.serialize(
      object.signal,
      specifiedType: const FullType(
          BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
    );
    yield r'threshold';
    yield serializers.serialize(
      object.threshold,
      specifiedType: const FullType(
          BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
    );
    if (object.runbook != null) {
      yield r'runbook';
      yield serializers.serialize(
        object.runbook,
        specifiedType: const FullType.nullable(String),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    AlertState object, {
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
    required AlertStateBuilder result,
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
        case r'name':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.name = valueDes;
          break;
        case r'severity':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.severity = valueDes;
          break;
        case r'firing':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.firing = valueDes;
          break;
        case r'status':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.status = valueDes;
          break;
        case r'since':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.since = valueDes;
          break;
        case r'signal':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(
                BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
          ) as BuiltMap<String, JsonObject?>;
          result.signal.replace(valueDes);
          break;
        case r'threshold':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(
                BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
          ) as BuiltMap<String, JsonObject?>;
          result.threshold.replace(valueDes);
          break;
        case r'runbook':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.runbook = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AlertState deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AlertStateBuilder();
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
