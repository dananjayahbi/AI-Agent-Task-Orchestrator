//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/code_enum.dart';
import 'package:built_value/json_object.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'error_envelope_body.g.dart';

/// The five Section 9.2 fields, in wire order, as they sit under ``error``.
///
/// Properties:
/// * [code]
/// * [message]
/// * [retryable]
/// * [details]
/// * [correlationId]
@BuiltValue()
abstract class ErrorEnvelopeBody
    implements Built<ErrorEnvelopeBody, ErrorEnvelopeBodyBuilder> {
  @BuiltValueField(wireName: r'code')
  CodeEnum get code;
  // enum codeEnum {  AUTH_REQUIRED,  AUTH_FORBIDDEN_PROJECT,  VALIDATION_ERROR,  TASK_NOT_FOUND,  TASK_STATE_CONFLICT,  TASK_ALREADY_CLAIMED,  LEASE_EXPIRED,  LEASE_NOT_OWNED,  DEPENDENCY_UNMET,  CONCURRENCY_LIMIT_REACHED,  SCOPE_VIOLATION,  ROLE_NOT_PERMITTED,  AUDITOR_SAME_AS_CODER,  ATTACHMENT_NOT_READY,  ATTACHMENT_UNSUPPORTED_FORMAT,  POLICY_VIOLATION,  RATE_LIMITED,  VERSION_CONFLICT,  SERVER_ERROR,  };

  @BuiltValueField(wireName: r'message')
  String get message;

  @BuiltValueField(wireName: r'retryable')
  bool get retryable;

  @BuiltValueField(wireName: r'details')
  BuiltMap<String, JsonObject?>? get details;

  @BuiltValueField(wireName: r'correlation_id')
  String get correlationId;

  ErrorEnvelopeBody._();

  factory ErrorEnvelopeBody([void updates(ErrorEnvelopeBodyBuilder b)]) =
      _$ErrorEnvelopeBody;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ErrorEnvelopeBodyBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<ErrorEnvelopeBody> get serializer =>
      _$ErrorEnvelopeBodySerializer();
}

class _$ErrorEnvelopeBodySerializer
    implements PrimitiveSerializer<ErrorEnvelopeBody> {
  @override
  final Iterable<Type> types = const [ErrorEnvelopeBody, _$ErrorEnvelopeBody];

  @override
  final String wireName = r'ErrorEnvelopeBody';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ErrorEnvelopeBody object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'code';
    yield serializers.serialize(
      object.code,
      specifiedType: const FullType(CodeEnum),
    );
    yield r'message';
    yield serializers.serialize(
      object.message,
      specifiedType: const FullType(String),
    );
    yield r'retryable';
    yield serializers.serialize(
      object.retryable,
      specifiedType: const FullType(bool),
    );
    if (object.details != null) {
      yield r'details';
      yield serializers.serialize(
        object.details,
        specifiedType: const FullType.nullable(
            BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
      );
    }
    yield r'correlation_id';
    yield serializers.serialize(
      object.correlationId,
      specifiedType: const FullType(String),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    ErrorEnvelopeBody object, {
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
    required ErrorEnvelopeBodyBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'code':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(CodeEnum),
          ) as CodeEnum;
          result.code = valueDes;
          break;
        case r'message':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.message = valueDes;
          break;
        case r'retryable':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(bool),
          ) as bool;
          result.retryable = valueDes;
          break;
        case r'details':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(
                BuiltMap, [FullType(String), FullType.nullable(JsonObject)]),
          ) as BuiltMap<String, JsonObject?>?;
          if (valueDes == null) continue;
          result.details.replace(valueDes);
          break;
        case r'correlation_id':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(String),
          ) as String;
          result.correlationId = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ErrorEnvelopeBody deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ErrorEnvelopeBodyBuilder();
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
