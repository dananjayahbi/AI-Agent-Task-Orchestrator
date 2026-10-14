//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:orchestrator_mobile/src/model/result_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'merge_result_request.g.dart';

/// ``POST /merge/{task}/result`` input (Section 9.2; MT-3.7-01).
///
/// Properties:
/// * [result] - succeeded | conflict | failed — the executor's reported outcome; succeeded applies T17, the other two apply T18 with that flavor (Section 7.2 values, never inferred).  * `succeeded` - succeeded * `conflict` - conflict * `failed` - failed
/// * [sha] - The resulting merge sha — **required for succeeded** (T17's Guard column; Section 11.4). Section 7.2 has no sha column, so it rides this payload, the history note and the event data (recorded reading; no silent schema change).
/// * [details] - Free-text outcome detail (conflict file list, error summary) — carried into the history note and the merge.failed event data.
/// * [version] - Optional task ``version`` the executor saw at start (FR-TSK-06) — a stale value answers VERSION_CONFLICT (409) and applies nothing.
@BuiltValue()
abstract class MergeResultRequest
    implements Built<MergeResultRequest, MergeResultRequestBuilder> {
  /// succeeded | conflict | failed — the executor's reported outcome; succeeded applies T17, the other two apply T18 with that flavor (Section 7.2 values, never inferred).  * `succeeded` - succeeded * `conflict` - conflict * `failed` - failed
  @BuiltValueField(wireName: r'result')
  ResultEnum get result;
  // enum resultEnum {  succeeded,  conflict,  failed,  };

  /// The resulting merge sha — **required for succeeded** (T17's Guard column; Section 11.4). Section 7.2 has no sha column, so it rides this payload, the history note and the event data (recorded reading; no silent schema change).
  @BuiltValueField(wireName: r'sha')
  String? get sha;

  /// Free-text outcome detail (conflict file list, error summary) — carried into the history note and the merge.failed event data.
  @BuiltValueField(wireName: r'details')
  String? get details;

  /// Optional task ``version`` the executor saw at start (FR-TSK-06) — a stale value answers VERSION_CONFLICT (409) and applies nothing.
  @BuiltValueField(wireName: r'version')
  int? get version;

  MergeResultRequest._();

  factory MergeResultRequest([void updates(MergeResultRequestBuilder b)]) =
      _$MergeResultRequest;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(MergeResultRequestBuilder b) => b
    ..sha = ''
    ..details = '';

  @BuiltValueSerializer(custom: true)
  static Serializer<MergeResultRequest> get serializer =>
      _$MergeResultRequestSerializer();
}

class _$MergeResultRequestSerializer
    implements PrimitiveSerializer<MergeResultRequest> {
  @override
  final Iterable<Type> types = const [MergeResultRequest, _$MergeResultRequest];

  @override
  final String wireName = r'MergeResultRequest';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    MergeResultRequest object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    yield r'result';
    yield serializers.serialize(
      object.result,
      specifiedType: const FullType(ResultEnum),
    );
    if (object.sha != null) {
      yield r'sha';
      yield serializers.serialize(
        object.sha,
        specifiedType: const FullType(String),
      );
    }
    if (object.details != null) {
      yield r'details';
      yield serializers.serialize(
        object.details,
        specifiedType: const FullType(String),
      );
    }
    if (object.version != null) {
      yield r'version';
      yield serializers.serialize(
        object.version,
        specifiedType: const FullType(int),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    MergeResultRequest object, {
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
    required MergeResultRequestBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'result':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType(ResultEnum),
          ) as ResultEnum;
          result.result = valueDes;
          break;
        case r'sha':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.sha = valueDes;
          break;
        case r'details':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.details = valueDes;
          break;
        case r'version':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.version = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  MergeResultRequest deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = MergeResultRequestBuilder();
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
