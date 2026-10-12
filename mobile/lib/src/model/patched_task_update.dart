//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/priority_enum.dart';
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'patched_task_update.g.dart';

/// PATCH /tasks/{id} body — FR-TSK-02 fields + the FR-TSK-06 version.
///
/// Properties:
/// * [version] - The version the client saw (required — FR-TSK-06). A stale value answers VERSION_CONFLICT; a match applies and increments.
/// * [title]
/// * [description]
/// * [acceptanceCriteria]
/// * [targetScope]
/// * [testCommand]
/// * [priority]
/// * [dependsOn] - Replace-the-set dependency write (MT-1.4-05): the payload becomes the full set — omit to leave it untouched, `[]` clears it. Validated under the version check, same transaction.
@BuiltValue()
abstract class PatchedTaskUpdate
    implements Built<PatchedTaskUpdate, PatchedTaskUpdateBuilder> {
  /// The version the client saw (required — FR-TSK-06). A stale value answers VERSION_CONFLICT; a match applies and increments.
  @BuiltValueField(wireName: r'version')
  int? get version;

  @BuiltValueField(wireName: r'title')
  String? get title;

  @BuiltValueField(wireName: r'description')
  String? get description;

  @BuiltValueField(wireName: r'acceptance_criteria')
  BuiltList<String>? get acceptanceCriteria;

  @BuiltValueField(wireName: r'target_scope')
  BuiltList<String>? get targetScope;

  @BuiltValueField(wireName: r'test_command')
  String? get testCommand;

  @BuiltValueField(wireName: r'priority')
  PriorityEnum? get priority;
  // enum priorityEnum {  urgent,  high,  medium,  low,  };

  /// Replace-the-set dependency write (MT-1.4-05): the payload becomes the full set — omit to leave it untouched, `[]` clears it. Validated under the version check, same transaction.
  @BuiltValueField(wireName: r'depends_on')
  BuiltList<String>? get dependsOn;

  PatchedTaskUpdate._();

  factory PatchedTaskUpdate([void updates(PatchedTaskUpdateBuilder b)]) =
      _$PatchedTaskUpdate;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(PatchedTaskUpdateBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<PatchedTaskUpdate> get serializer =>
      _$PatchedTaskUpdateSerializer();
}

class _$PatchedTaskUpdateSerializer
    implements PrimitiveSerializer<PatchedTaskUpdate> {
  @override
  final Iterable<Type> types = const [PatchedTaskUpdate, _$PatchedTaskUpdate];

  @override
  final String wireName = r'PatchedTaskUpdate';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    PatchedTaskUpdate object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    if (object.version != null) {
      yield r'version';
      yield serializers.serialize(
        object.version,
        specifiedType: const FullType(int),
      );
    }
    if (object.title != null) {
      yield r'title';
      yield serializers.serialize(
        object.title,
        specifiedType: const FullType(String),
      );
    }
    if (object.description != null) {
      yield r'description';
      yield serializers.serialize(
        object.description,
        specifiedType: const FullType(String),
      );
    }
    if (object.acceptanceCriteria != null) {
      yield r'acceptance_criteria';
      yield serializers.serialize(
        object.acceptanceCriteria,
        specifiedType: const FullType(BuiltList, [FullType(String)]),
      );
    }
    if (object.targetScope != null) {
      yield r'target_scope';
      yield serializers.serialize(
        object.targetScope,
        specifiedType: const FullType(BuiltList, [FullType(String)]),
      );
    }
    if (object.testCommand != null) {
      yield r'test_command';
      yield serializers.serialize(
        object.testCommand,
        specifiedType: const FullType(String),
      );
    }
    if (object.priority != null) {
      yield r'priority';
      yield serializers.serialize(
        object.priority,
        specifiedType: const FullType(PriorityEnum),
      );
    }
    if (object.dependsOn != null) {
      yield r'depends_on';
      yield serializers.serialize(
        object.dependsOn,
        specifiedType: const FullType(BuiltList, [FullType(String)]),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    PatchedTaskUpdate object, {
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
    required PatchedTaskUpdateBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'version':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.version = valueDes;
          break;
        case r'title':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.title = valueDes;
          break;
        case r'description':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.description = valueDes;
          break;
        case r'acceptance_criteria':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.acceptanceCriteria.replace(valueDes);
          break;
        case r'target_scope':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.targetScope.replace(valueDes);
          break;
        case r'test_command':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.testCommand = valueDes;
          break;
        case r'priority':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(PriorityEnum),
          ) as PriorityEnum?;
          if (valueDes == null) continue;
          result.priority = valueDes;
          break;
        case r'depends_on':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.dependsOn.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  PatchedTaskUpdate deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = PatchedTaskUpdateBuilder();
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
