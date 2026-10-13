//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/audit_report.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'audit_report_list_envelope.g.dart';

/// pagination.md envelope: exactly ``results`` + ``next_cursor``.
///
/// Properties:
/// * [results]
/// * [nextCursor] - Opaque cursor for the next page; null = end of list.
@BuiltValue()
abstract class AuditReportListEnvelope
    implements Built<AuditReportListEnvelope, AuditReportListEnvelopeBuilder> {
  @BuiltValueField(wireName: r'results')
  BuiltList<AuditReport> get results;

  /// Opaque cursor for the next page; null = end of list.
  @BuiltValueField(wireName: r'next_cursor')
  String? get nextCursor;

  AuditReportListEnvelope._();

  factory AuditReportListEnvelope(
          [void updates(AuditReportListEnvelopeBuilder b)]) =
      _$AuditReportListEnvelope;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(AuditReportListEnvelopeBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<AuditReportListEnvelope> get serializer =>
      _$AuditReportListEnvelopeSerializer();
}

class _$AuditReportListEnvelopeSerializer
    implements PrimitiveSerializer<AuditReportListEnvelope> {
  @override
  final Iterable<Type> types = const [
    AuditReportListEnvelope,
    _$AuditReportListEnvelope
  ];

  @override
  final String wireName = r'AuditReportListEnvelope';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    AuditReportListEnvelope object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'results';
    yield serializers.serialize(
      object.results,
      specifiedType: const FullType(BuiltList, [FullType(AuditReport)]),
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
    AuditReportListEnvelope object, {
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
    required AuditReportListEnvelopeBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'results':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(BuiltList, [FullType(AuditReport)]),
          ) as BuiltList<AuditReport>;
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
  AuditReportListEnvelope deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = AuditReportListEnvelopeBuilder();
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
