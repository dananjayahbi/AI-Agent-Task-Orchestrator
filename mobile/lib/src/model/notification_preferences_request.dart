//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/notification_preference.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'notification_preferences_request.g.dart';

/// ``PUT`` body: a non-empty list of preference pairs to update.
///
/// Properties:
/// * [preferences]
@BuiltValue()
abstract class NotificationPreferencesRequest
    implements
        Built<NotificationPreferencesRequest,
            NotificationPreferencesRequestBuilder> {
  @BuiltValueField(wireName: r'preferences')
  BuiltList<NotificationPreference> get preferences;

  NotificationPreferencesRequest._();

  factory NotificationPreferencesRequest(
          [void updates(NotificationPreferencesRequestBuilder b)]) =
      _$NotificationPreferencesRequest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(NotificationPreferencesRequestBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<NotificationPreferencesRequest> get serializer =>
      _$NotificationPreferencesRequestSerializer();
}

class _$NotificationPreferencesRequestSerializer
    implements PrimitiveSerializer<NotificationPreferencesRequest> {
  @override
  final Iterable<Type> types = const [
    NotificationPreferencesRequest,
    _$NotificationPreferencesRequest
  ];

  @override
  final String wireName = r'NotificationPreferencesRequest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    NotificationPreferencesRequest object, {
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
    NotificationPreferencesRequest object, {
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
    required NotificationPreferencesRequestBuilder result,
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
  NotificationPreferencesRequest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = NotificationPreferencesRequestBuilder();
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
