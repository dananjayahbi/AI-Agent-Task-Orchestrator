//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/event_type_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'notification_preference.g.dart';

/// One ``{event_type, enabled}`` pair — the wire shape both clients edit.
///
/// Properties:
/// * [eventType]
/// * [enabled]
@BuiltValue()
abstract class NotificationPreference
    implements Built<NotificationPreference, NotificationPreferenceBuilder> {
  @BuiltValueField(wireName: r'event_type')
  EventTypeEnum get eventType;
  // enum eventTypeEnum {  in_human_review,  merge_failure,  retry_exhaustion,  completion_digest,  };

  @BuiltValueField(wireName: r'enabled')
  bool get enabled;

  NotificationPreference._();

  factory NotificationPreference(
          [void updates(NotificationPreferenceBuilder b)]) =
      _$NotificationPreference;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(NotificationPreferenceBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<NotificationPreference> get serializer =>
      _$NotificationPreferenceSerializer();
}

class _$NotificationPreferenceSerializer
    implements PrimitiveSerializer<NotificationPreference> {
  @override
  final Iterable<Type> types = const [
    NotificationPreference,
    _$NotificationPreference
  ];

  @override
  final String wireName = r'NotificationPreference';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    NotificationPreference object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'event_type';
    yield serializers.serialize(
      object.eventType,
      specifiedType: const FullType(EventTypeEnum),
    );
    yield r'enabled';
    yield serializers.serialize(
      object.enabled,
      specifiedType: const FullType(bool),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    NotificationPreference object, {
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
    required NotificationPreferenceBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'event_type':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(EventTypeEnum),
          ) as EventTypeEnum;
          result.eventType = valueDes;
          break;
        case r'enabled':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.enabled = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  NotificationPreference deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = NotificationPreferenceBuilder();
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
