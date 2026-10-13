//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'attachment_delete.g.dart';

/// MT-1.11-05's DELETE response — the soft-deleted record's marker.
///
/// Properties:
/// * [id] - The deleted attachment's identity.
/// * [taskId] - The owning task.
/// * [deletedAt] - Server time of the soft delete (MT-1.11-05): the retention job (Section 9.9) owns the hard removal (Section 16.3).
@BuiltValue()
abstract class AttachmentDelete
    implements Built<AttachmentDelete, AttachmentDeleteBuilder> {
  /// The deleted attachment's identity.
  @BuiltValueField(wireName: r'id')
  String get id;

  /// The owning task.
  @BuiltValueField(wireName: r'task_id')
  String get taskId;

  /// Server time of the soft delete (MT-1.11-05): the retention job (Section 9.9) owns the hard removal (Section 16.3).
  @BuiltValueField(wireName: r'deleted_at')
  DateTime get deletedAt;

  AttachmentDelete._();

  factory AttachmentDelete([void updates(AttachmentDeleteBuilder b)]) =
      _$AttachmentDelete;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AttachmentDeleteBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AttachmentDelete> get serializer =>
      _$AttachmentDeleteSerializer();
}

class _$AttachmentDeleteSerializer
    implements PrimitiveSerializer<AttachmentDelete> {
  @override
  final Iterable<Type> types = const [AttachmentDelete, _$AttachmentDelete];

  @override
  final String wireName = r'AttachmentDelete';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AttachmentDelete object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'id';
    yield serializers.serialize(
      object.id,
      specifiedType: const FullType(String),
    );
    yield r'task_id';
    yield serializers.serialize(
      object.taskId,
      specifiedType: const FullType(String),
    );
    yield r'deleted_at';
    yield serializers.serialize(
      object.deletedAt,
      specifiedType: const FullType(DateTime),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    AttachmentDelete object, {
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
    required AttachmentDeleteBuilder result,
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
        case r'task_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.taskId = valueDes;
          break;
        case r'deleted_at':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(DateTime),
          ) as DateTime;
          result.deletedAt = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AttachmentDelete deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AttachmentDeleteBuilder();
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
