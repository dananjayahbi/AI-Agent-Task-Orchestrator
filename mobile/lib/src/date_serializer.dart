// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

import 'package:built_collection/built_collection.dart';
import 'package:built_value/serializer.dart';
import 'package:orchestrator_mobile/src/model/date.dart';

class DateSerializer implements PrimitiveSerializer<Date> {
  const DateSerializer();

  @override
  Iterable<Type> get types => BuiltList.of([Date]);

  @override
  String get wireName => 'Date';

  @override
  Date deserialize(Serializers serializers, Object serialized,
      {FullType specifiedType = FullType.unspecified}) {
    final parsed = DateTime.parse(serialized as String);
    return Date(parsed.year, parsed.month, parsed.day);
  }

  @override
  Object serialize(Serializers serializers, Date date,
      {FullType specifiedType = FullType.unspecified}) {
    return date.toString();
  }
}
