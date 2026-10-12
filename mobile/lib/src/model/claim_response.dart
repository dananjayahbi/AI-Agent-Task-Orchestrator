//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/rules_block.dart';
import 'package:orchestrator_mobile/src/model/lease_record.dart';
import 'package:orchestrator_mobile/src/model/task.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'claim_response.g.dart';

/// Section 9.3 step 6: task details, lease record, rules block.
///
/// Properties:
/// * [task]
/// * [lease]
/// * [rulesBlock]
@BuiltValue()
abstract class ClaimResponse
    implements Built<ClaimResponse, ClaimResponseBuilder> {
  @BuiltValueField(wireName: r'task')
  Task get task;

  @BuiltValueField(wireName: r'lease')
  LeaseRecord get lease;

  @BuiltValueField(wireName: r'rules_block')
  RulesBlock get rulesBlock;

  ClaimResponse._();

  factory ClaimResponse([void updates(ClaimResponseBuilder b)]) =
      _$ClaimResponse;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ClaimResponseBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<ClaimResponse> get serializer =>
      _$ClaimResponseSerializer();
}

class _$ClaimResponseSerializer implements PrimitiveSerializer<ClaimResponse> {
  @override
  final Iterable<Type> types = const [ClaimResponse, _$ClaimResponse];

  @override
  final String wireName = r'ClaimResponse';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ClaimResponse object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'task';
    yield serializers.serialize(
      object.task,
      specifiedType: const FullType(Task),
    );
    yield r'lease';
    yield serializers.serialize(
      object.lease,
      specifiedType: const FullType(LeaseRecord),
    );
    yield r'rules_block';
    yield serializers.serialize(
      object.rulesBlock,
      specifiedType: const FullType(RulesBlock),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    ClaimResponse object, {
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
    required ClaimResponseBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'task':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(Task),
          ) as Task;
          result.task.replace(valueDes);
          break;
        case r'lease':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(LeaseRecord),
          ) as LeaseRecord;
          result.lease.replace(valueDes);
          break;
        case r'rules_block':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(RulesBlock),
          ) as RulesBlock;
          result.rulesBlock.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ClaimResponse deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ClaimResponseBuilder();
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
