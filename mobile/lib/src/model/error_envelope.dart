//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/error_envelope_body.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'error_envelope.g.dart';

/// The Section 9.2 wire envelope — five fields nested under ``error``.  ``apps.core.errors.build_error_envelope`` emits the wrapper on the wire; the document must model that nesting, not a flat top-level body (the flat schema was a contract bug, fixed at the Wave 2 end-of-wave gate).
///
/// Properties:
/// * [error]
@BuiltValue()
abstract class ErrorEnvelope
    implements Built<ErrorEnvelope, ErrorEnvelopeBuilder> {
  @BuiltValueField(wireName: r'error')
  ErrorEnvelopeBody get error;

  ErrorEnvelope._();

  factory ErrorEnvelope([void updates(ErrorEnvelopeBuilder b)]) =
      _$ErrorEnvelope;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(ErrorEnvelopeBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<ErrorEnvelope> get serializer =>
      _$ErrorEnvelopeSerializer();
}

class _$ErrorEnvelopeSerializer implements PrimitiveSerializer<ErrorEnvelope> {
  @override
  final Iterable<Type> types = const [ErrorEnvelope, _$ErrorEnvelope];

  @override
  final String wireName = r'ErrorEnvelope';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    ErrorEnvelope object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'error';
    yield serializers.serialize(
      object.error,
      specifiedType: const FullType(ErrorEnvelopeBody),
    );
  }

  @override
  Object serialize(
    Serializers serializers,
    ErrorEnvelope object, {
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
    required ErrorEnvelopeBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'error':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(ErrorEnvelopeBody),
          ) as ErrorEnvelopeBody;
          result.error.replace(valueDes);
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  ErrorEnvelope deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = ErrorEnvelopeBuilder();
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
