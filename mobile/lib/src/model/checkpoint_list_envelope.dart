//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/checkpoint.dart';
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'checkpoint_list_envelope.g.dart';

/// pagination.md envelope: exactly ``results`` + ``next_cursor``.
///
/// Properties:
/// * [results]
/// * [nextCursor] - Opaque cursor for the next page; null = end of list.
@BuiltValue()
abstract class CheckpointListEnvelope
    implements Built<CheckpointListEnvelope, CheckpointListEnvelopeBuilder> {
  @BuiltValueField(wireName: r'results')
  BuiltList<Checkpoint> get results;

  /// Opaque cursor for the next page; null = end of list.
  @BuiltValueField(wireName: r'next_cursor')
  String? get nextCursor;

  CheckpointListEnvelope._();

  factory CheckpointListEnvelope(
          [void updates(CheckpointListEnvelopeBuilder b)]) =
      _$CheckpointListEnvelope;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(CheckpointListEnvelopeBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<CheckpointListEnvelope> get serializer =>
      _$CheckpointListEnvelopeSerializer();
}

class _$CheckpointListEnvelopeSerializer
    implements PrimitiveSerializer<CheckpointListEnvelope> {
  @override
  final Iterable<Type> types = const [
    CheckpointListEnvelope,
    _$CheckpointListEnvelope
  ];

  @override
  final String wireName = r'CheckpointListEnvelope';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    CheckpointListEnvelope object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'results';
    yield serializers.serialize(
      object.results,
      specifiedType: const FullType(BuiltList, [FullType(Checkpoint)]),
    );
    yield r'next_cursor';
    yield object.nextCursor == null
        ? null
        : serializers.serialize(
            object.nextCursor,
            specifiedType: const FullType.nullable(String),
          );
  }

  @override
  Object serialize(
    Serializers serializers,
    CheckpointListEnvelope object, {
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
    required CheckpointListEnvelopeBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'results':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(BuiltList, [FullType(Checkpoint)]),
          ) as BuiltList<Checkpoint>;
          result.results.replace(valueDes);
          break;
        case r'next_cursor':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.nextCursor = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  CheckpointListEnvelope deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = CheckpointListEnvelopeBuilder();
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
