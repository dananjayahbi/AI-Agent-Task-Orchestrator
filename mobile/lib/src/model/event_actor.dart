//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/event_actor_type_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'event_actor.g.dart';

/// Envelope ``actor`` — the structured Section 9.6 object, never flattened.
///
/// Properties:
/// * [type]
/// * [ref]
@BuiltValue()
abstract class EventActor implements Built<EventActor, EventActorBuilder> {
  @BuiltValueField(wireName: r'type')
  EventActorTypeEnum get type;
  // enum typeEnum {  owner,  agent,  system,  };

  @BuiltValueField(wireName: r'ref')
  String get ref;

  EventActor._();

  factory EventActor([void updates(EventActorBuilder b)]) = _$EventActor;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(EventActorBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<EventActor> get serializer => _$EventActorSerializer();
}

class _$EventActorSerializer implements PrimitiveSerializer<EventActor> {
  @override
  final Iterable<Type> types = const [EventActor, _$EventActor];

  @override
  final String wireName = r'EventActor';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    EventActor object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'type';
    yield serializers.serialize(
      object.type,
      specifiedType: const FullType(EventActorTypeEnum),
    );
    yield r'ref';
    yield serializers.serialize(
      object.ref,
      specifiedType: const FullType(String),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    EventActor object, {
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
    required EventActorBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'type':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(EventActorTypeEnum),
          ) as EventActorTypeEnum;
          result.type = valueDes;
          break;
        case r'ref':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.ref = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  EventActor deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = EventActorBuilder();
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
