//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/notification_preference.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'notification_preferences_response.g.dart';

/// ``GET``/``PUT`` response: every Section 9.8 type with its switch.
///
/// Properties:
/// * [preferences]
@BuiltValue()
abstract class NotificationPreferencesResponse
    implements
        Built<NotificationPreferencesResponse,
            NotificationPreferencesResponseBuilder> {
  @BuiltValueField(wireName: r'preferences')
  BuiltList<NotificationPreference> get preferences;

  NotificationPreferencesResponse._();

  factory NotificationPreferencesResponse(
          [void updates(NotificationPreferencesResponseBuilder b)]) =
      _$NotificationPreferencesResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(NotificationPreferencesResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<NotificationPreferencesResponse> get serializer =>
      _$NotificationPreferencesResponseSerializer();
}

class _$NotificationPreferencesResponseSerializer
    implements PrimitiveSerializer<NotificationPreferencesResponse> {
  @override
  final Iterable<Type> types = const [
    NotificationPreferencesResponse,
    _$NotificationPreferencesResponse
  ];

  @override
  final String wireName = r'NotificationPreferencesResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    NotificationPreferencesResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'preferences';
    yield serializers.serialize(
      object.preferences,
      specifiedType:
          const FullType(BuiltList, [FullType(NotificationPreference)]),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    NotificationPreferencesResponse object, {
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
    required NotificationPreferencesResponseBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'preferences':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType(BuiltList, [FullType(NotificationPreference)]),
          ) as BuiltList<NotificationPreference>;
          result.preferences.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  NotificationPreferencesResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = NotificationPreferencesResponseBuilder();
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
