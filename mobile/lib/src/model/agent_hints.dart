//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'agent_hints.g.dart';

/// Section 10.3 ``agent_hints`` — every key optional.
///
/// Properties:
/// * [testCommandDefault] - Fallback test-command hint (Section 10.3 example: \"see task\").
/// * [worktreeMode] - Per-task worktree advice (Section 10.3 example: false; ADR-013).
@BuiltValue()
abstract class AgentHints implements Built<AgentHints, AgentHintsBuilder> {
  /// Fallback test-command hint (Section 10.3 example: \"see task\").
  @BuiltValueField(wireName: r'test_command_default')
  String? get testCommandDefault;

  /// Per-task worktree advice (Section 10.3 example: false; ADR-013).
  @BuiltValueField(wireName: r'worktree_mode')
  bool? get worktreeMode;

  AgentHints._();

  factory AgentHints([void updates(AgentHintsBuilder b)]) = _$AgentHints;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AgentHintsBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AgentHints> get serializer => _$AgentHintsSerializer();
}

class _$AgentHintsSerializer implements PrimitiveSerializer<AgentHints> {
  @override
  final Iterable<Type> types = const [AgentHints, _$AgentHints];

  @override
  final String wireName = r'AgentHints';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AgentHints object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    if (object.testCommandDefault != null) {
      yield r'test_command_default';
      yield serializers.serialize(
        object.testCommandDefault,
        specifiedType: const FullType(String),
      );
    }
    if (object.worktreeMode != null) {
      yield r'worktree_mode';
      yield serializers.serialize(
        object.worktreeMode,
        specifiedType: const FullType(bool),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    AgentHints object, {
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
    required AgentHintsBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'test_command_default':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.testCommandDefault = valueDes;
          break;
        case r'worktree_mode':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(bool),
          ) as bool?;
          if (valueDes == null) continue;
          result.worktreeMode = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  AgentHints deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AgentHintsBuilder();
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
