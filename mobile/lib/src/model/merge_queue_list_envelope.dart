//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/merge_queue_item.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'merge_queue_list_envelope.g.dart';

/// pagination.md envelope: exactly ``results`` + ``next_cursor``.
///
/// Properties:
/// * [results]
/// * [nextCursor] - Opaque cursor for the next page; null = end of list.
@BuiltValue()
abstract class MergeQueueListEnvelope
    implements Built<MergeQueueListEnvelope, MergeQueueListEnvelopeBuilder> {
  @BuiltValueField(wireName: r'results')
  BuiltList<MergeQueueItem> get results;

  /// Opaque cursor for the next page; null = end of list.
  @BuiltValueField(wireName: r'next_cursor')
  String? get nextCursor;

  MergeQueueListEnvelope._();

  factory MergeQueueListEnvelope(
          [void updates(MergeQueueListEnvelopeBuilder b)]) =
      _$MergeQueueListEnvelope;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(MergeQueueListEnvelopeBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<MergeQueueListEnvelope> get serializer =>
      _$MergeQueueListEnvelopeSerializer();
}

class _$MergeQueueListEnvelopeSerializer
    implements PrimitiveSerializer<MergeQueueListEnvelope> {
  @override
  final Iterable<Type> types = const [
    MergeQueueListEnvelope,
    _$MergeQueueListEnvelope
  ];

  @override
  final String wireName = r'MergeQueueListEnvelope';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    MergeQueueListEnvelope object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'results';
    yield serializers.serialize(
      object.results,
      specifiedType: const FullType(BuiltList, [FullType(MergeQueueItem)]),
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
    MergeQueueListEnvelope object, {
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
    required MergeQueueListEnvelopeBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'results':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType(BuiltList, [FullType(MergeQueueItem)]),
          ) as BuiltList<MergeQueueItem>;
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
  MergeQueueListEnvelope deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = MergeQueueListEnvelopeBuilder();
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
