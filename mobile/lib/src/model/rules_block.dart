//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'rules_block.g.dart';

/// Section 10.6 rules block: standard rules + project rules appended.
///
/// Properties:
/// * [standardRules]
/// * [projectRules]
@BuiltValue()
abstract class RulesBlock implements Built<RulesBlock, RulesBlockBuilder> {
  @BuiltValueField(wireName: r'standard_rules')
  BuiltList<String> get standardRules;

  @BuiltValueField(wireName: r'project_rules')
  String get projectRules;

  RulesBlock._();

  factory RulesBlock([void updates(RulesBlockBuilder b)]) = _$RulesBlock;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(RulesBlockBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<RulesBlock> get serializer => _$RulesBlockSerializer();
}

class _$RulesBlockSerializer implements PrimitiveSerializer<RulesBlock> {
  @override
  final Iterable<Type> types = const [RulesBlock, _$RulesBlock];

  @override
  final String wireName = r'RulesBlock';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    RulesBlock object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'standard_rules';
    yield serializers.serialize(
      object.standardRules,
      specifiedType: const FullType(BuiltList, [FullType(String)]),
    );
    yield r'project_rules';
    yield serializers.serialize(
      object.projectRules,
      specifiedType: const FullType(String),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    RulesBlock object, {
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
    required RulesBlockBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'standard_rules':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(BuiltList, [FullType(String)]),
          ) as BuiltList<String>;
          result.standardRules.replace(valueDes);
          break;
        case r'project_rules':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.projectRules = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  RulesBlock deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = RulesBlockBuilder();
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
