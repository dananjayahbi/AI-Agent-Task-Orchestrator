//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'code_enum.g.dart';

/// * `AUTH_REQUIRED` - AUTH_REQUIRED * `AUTH_FORBIDDEN_PROJECT` - AUTH_FORBIDDEN_PROJECT * `VALIDATION_ERROR` - VALIDATION_ERROR * `TASK_NOT_FOUND` - TASK_NOT_FOUND * `TASK_STATE_CONFLICT` - TASK_STATE_CONFLICT * `TASK_ALREADY_CLAIMED` - TASK_ALREADY_CLAIMED * `LEASE_EXPIRED` - LEASE_EXPIRED * `LEASE_NOT_OWNED` - LEASE_NOT_OWNED * `DEPENDENCY_UNMET` - DEPENDENCY_UNMET * `CONCURRENCY_LIMIT_REACHED` - CONCURRENCY_LIMIT_REACHED * `SCOPE_VIOLATION` - SCOPE_VIOLATION * `ROLE_NOT_PERMITTED` - ROLE_NOT_PERMITTED * `AUDITOR_SAME_AS_CODER` - AUDITOR_SAME_AS_CODER * `ATTACHMENT_NOT_READY` - ATTACHMENT_NOT_READY * `ATTACHMENT_UNSUPPORTED_FORMAT` - ATTACHMENT_UNSUPPORTED_FORMAT * `POLICY_VIOLATION` - POLICY_VIOLATION * `RATE_LIMITED` - RATE_LIMITED * `VERSION_CONFLICT` - VERSION_CONFLICT * `SERVER_ERROR` - SERVER_ERROR
class CodeEnum extends EnumClass {
  @BuiltValueEnumConst(wireName: r'AUTH_REQUIRED')
  static const CodeEnum AUTH_REQUIRED = _$AUTH_REQUIRED;
  @BuiltValueEnumConst(wireName: r'AUTH_FORBIDDEN_PROJECT')
  static const CodeEnum AUTH_FORBIDDEN_PROJECT = _$AUTH_FORBIDDEN_PROJECT;
  @BuiltValueEnumConst(wireName: r'VALIDATION_ERROR')
  static const CodeEnum VALIDATION_ERROR = _$VALIDATION_ERROR;
  @BuiltValueEnumConst(wireName: r'TASK_NOT_FOUND')
  static const CodeEnum TASK_NOT_FOUND = _$TASK_NOT_FOUND;
  @BuiltValueEnumConst(wireName: r'TASK_STATE_CONFLICT')
  static const CodeEnum TASK_STATE_CONFLICT = _$TASK_STATE_CONFLICT;
  @BuiltValueEnumConst(wireName: r'TASK_ALREADY_CLAIMED')
  static const CodeEnum TASK_ALREADY_CLAIMED = _$TASK_ALREADY_CLAIMED;
  @BuiltValueEnumConst(wireName: r'LEASE_EXPIRED')
  static const CodeEnum LEASE_EXPIRED = _$LEASE_EXPIRED;
  @BuiltValueEnumConst(wireName: r'LEASE_NOT_OWNED')
  static const CodeEnum LEASE_NOT_OWNED = _$LEASE_NOT_OWNED;
  @BuiltValueEnumConst(wireName: r'DEPENDENCY_UNMET')
  static const CodeEnum DEPENDENCY_UNMET = _$DEPENDENCY_UNMET;
  @BuiltValueEnumConst(wireName: r'CONCURRENCY_LIMIT_REACHED')
  static const CodeEnum CONCURRENCY_LIMIT_REACHED = _$CONCURRENCY_LIMIT_REACHED;
  @BuiltValueEnumConst(wireName: r'SCOPE_VIOLATION')
  static const CodeEnum SCOPE_VIOLATION = _$SCOPE_VIOLATION;
  @BuiltValueEnumConst(wireName: r'ROLE_NOT_PERMITTED')
  static const CodeEnum ROLE_NOT_PERMITTED = _$ROLE_NOT_PERMITTED;
  @BuiltValueEnumConst(wireName: r'AUDITOR_SAME_AS_CODER')
  static const CodeEnum AUDITOR_SAME_AS_CODER = _$AUDITOR_SAME_AS_CODER;
  @BuiltValueEnumConst(wireName: r'ATTACHMENT_NOT_READY')
  static const CodeEnum ATTACHMENT_NOT_READY = _$ATTACHMENT_NOT_READY;
  @BuiltValueEnumConst(wireName: r'ATTACHMENT_UNSUPPORTED_FORMAT')
  static const CodeEnum ATTACHMENT_UNSUPPORTED_FORMAT =
      _$ATTACHMENT_UNSUPPORTED_FORMAT;
  @BuiltValueEnumConst(wireName: r'POLICY_VIOLATION')
  static const CodeEnum POLICY_VIOLATION = _$POLICY_VIOLATION;
  @BuiltValueEnumConst(wireName: r'RATE_LIMITED')
  static const CodeEnum RATE_LIMITED = _$RATE_LIMITED;
  @BuiltValueEnumConst(wireName: r'VERSION_CONFLICT')
  static const CodeEnum VERSION_CONFLICT = _$VERSION_CONFLICT;
  @BuiltValueEnumConst(wireName: r'SERVER_ERROR')
  static const CodeEnum SERVER_ERROR = _$SERVER_ERROR;

  static Serializer<CodeEnum> get serializer => _$codeEnumSerializer;

  const CodeEnum._(String name) : super(name);

  static BuiltSet<CodeEnum> get values => _$values;
  static CodeEnum valueOf(String name) => _$valueOf(name);
}

/// Optionally, enum_class can generate a mixin to go with your enum for use
/// with Angular. It exposes your enum constants as getters. So, if you mix it
/// in to your Dart component class, the values become available to the
/// corresponding Angular template.
///
/// Trigger mixin generation by writing a line like this one next to your enum.
abstract class CodeEnumMixin = Object with _$CodeEnumMixin;
