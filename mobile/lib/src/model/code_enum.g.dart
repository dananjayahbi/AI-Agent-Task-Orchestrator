// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'code_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const CodeEnum _$AUTH_REQUIRED = const CodeEnum._('AUTH_REQUIRED');
const CodeEnum _$AUTH_FORBIDDEN_PROJECT =
    const CodeEnum._('AUTH_FORBIDDEN_PROJECT');
const CodeEnum _$VALIDATION_ERROR = const CodeEnum._('VALIDATION_ERROR');
const CodeEnum _$TASK_NOT_FOUND = const CodeEnum._('TASK_NOT_FOUND');
const CodeEnum _$TASK_STATE_CONFLICT = const CodeEnum._('TASK_STATE_CONFLICT');
const CodeEnum _$TASK_ALREADY_CLAIMED =
    const CodeEnum._('TASK_ALREADY_CLAIMED');
const CodeEnum _$LEASE_EXPIRED = const CodeEnum._('LEASE_EXPIRED');
const CodeEnum _$LEASE_NOT_OWNED = const CodeEnum._('LEASE_NOT_OWNED');
const CodeEnum _$DEPENDENCY_UNMET = const CodeEnum._('DEPENDENCY_UNMET');
const CodeEnum _$CONCURRENCY_LIMIT_REACHED =
    const CodeEnum._('CONCURRENCY_LIMIT_REACHED');
const CodeEnum _$SCOPE_VIOLATION = const CodeEnum._('SCOPE_VIOLATION');
const CodeEnum _$ROLE_NOT_PERMITTED = const CodeEnum._('ROLE_NOT_PERMITTED');
const CodeEnum _$AUDITOR_SAME_AS_CODER =
    const CodeEnum._('AUDITOR_SAME_AS_CODER');
const CodeEnum _$ATTACHMENT_NOT_READY =
    const CodeEnum._('ATTACHMENT_NOT_READY');
const CodeEnum _$ATTACHMENT_UNSUPPORTED_FORMAT =
    const CodeEnum._('ATTACHMENT_UNSUPPORTED_FORMAT');
const CodeEnum _$POLICY_VIOLATION = const CodeEnum._('POLICY_VIOLATION');
const CodeEnum _$RATE_LIMITED = const CodeEnum._('RATE_LIMITED');
const CodeEnum _$VERSION_CONFLICT = const CodeEnum._('VERSION_CONFLICT');
const CodeEnum _$SERVER_ERROR = const CodeEnum._('SERVER_ERROR');

CodeEnum _$valueOf(String name) {
  switch (name) {
    case 'AUTH_REQUIRED':
      return _$AUTH_REQUIRED;
    case 'AUTH_FORBIDDEN_PROJECT':
      return _$AUTH_FORBIDDEN_PROJECT;
    case 'VALIDATION_ERROR':
      return _$VALIDATION_ERROR;
    case 'TASK_NOT_FOUND':
      return _$TASK_NOT_FOUND;
    case 'TASK_STATE_CONFLICT':
      return _$TASK_STATE_CONFLICT;
    case 'TASK_ALREADY_CLAIMED':
      return _$TASK_ALREADY_CLAIMED;
    case 'LEASE_EXPIRED':
      return _$LEASE_EXPIRED;
    case 'LEASE_NOT_OWNED':
      return _$LEASE_NOT_OWNED;
    case 'DEPENDENCY_UNMET':
      return _$DEPENDENCY_UNMET;
    case 'CONCURRENCY_LIMIT_REACHED':
      return _$CONCURRENCY_LIMIT_REACHED;
    case 'SCOPE_VIOLATION':
      return _$SCOPE_VIOLATION;
    case 'ROLE_NOT_PERMITTED':
      return _$ROLE_NOT_PERMITTED;
    case 'AUDITOR_SAME_AS_CODER':
      return _$AUDITOR_SAME_AS_CODER;
    case 'ATTACHMENT_NOT_READY':
      return _$ATTACHMENT_NOT_READY;
    case 'ATTACHMENT_UNSUPPORTED_FORMAT':
      return _$ATTACHMENT_UNSUPPORTED_FORMAT;
    case 'POLICY_VIOLATION':
      return _$POLICY_VIOLATION;
    case 'RATE_LIMITED':
      return _$RATE_LIMITED;
    case 'VERSION_CONFLICT':
      return _$VERSION_CONFLICT;
    case 'SERVER_ERROR':
      return _$SERVER_ERROR;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<CodeEnum> _$values = BuiltSet<CodeEnum>(const <CodeEnum>[
  _$AUTH_REQUIRED,
  _$AUTH_FORBIDDEN_PROJECT,
  _$VALIDATION_ERROR,
  _$TASK_NOT_FOUND,
  _$TASK_STATE_CONFLICT,
  _$TASK_ALREADY_CLAIMED,
  _$LEASE_EXPIRED,
  _$LEASE_NOT_OWNED,
  _$DEPENDENCY_UNMET,
  _$CONCURRENCY_LIMIT_REACHED,
  _$SCOPE_VIOLATION,
  _$ROLE_NOT_PERMITTED,
  _$AUDITOR_SAME_AS_CODER,
  _$ATTACHMENT_NOT_READY,
  _$ATTACHMENT_UNSUPPORTED_FORMAT,
  _$POLICY_VIOLATION,
  _$RATE_LIMITED,
  _$VERSION_CONFLICT,
  _$SERVER_ERROR,
]);

class _$CodeEnumMeta {
  const _$CodeEnumMeta();
  CodeEnum get AUTH_REQUIRED => _$AUTH_REQUIRED;
  CodeEnum get AUTH_FORBIDDEN_PROJECT => _$AUTH_FORBIDDEN_PROJECT;
  CodeEnum get VALIDATION_ERROR => _$VALIDATION_ERROR;
  CodeEnum get TASK_NOT_FOUND => _$TASK_NOT_FOUND;
  CodeEnum get TASK_STATE_CONFLICT => _$TASK_STATE_CONFLICT;
  CodeEnum get TASK_ALREADY_CLAIMED => _$TASK_ALREADY_CLAIMED;
  CodeEnum get LEASE_EXPIRED => _$LEASE_EXPIRED;
  CodeEnum get LEASE_NOT_OWNED => _$LEASE_NOT_OWNED;
  CodeEnum get DEPENDENCY_UNMET => _$DEPENDENCY_UNMET;
  CodeEnum get CONCURRENCY_LIMIT_REACHED => _$CONCURRENCY_LIMIT_REACHED;
  CodeEnum get SCOPE_VIOLATION => _$SCOPE_VIOLATION;
  CodeEnum get ROLE_NOT_PERMITTED => _$ROLE_NOT_PERMITTED;
  CodeEnum get AUDITOR_SAME_AS_CODER => _$AUDITOR_SAME_AS_CODER;
  CodeEnum get ATTACHMENT_NOT_READY => _$ATTACHMENT_NOT_READY;
  CodeEnum get ATTACHMENT_UNSUPPORTED_FORMAT => _$ATTACHMENT_UNSUPPORTED_FORMAT;
  CodeEnum get POLICY_VIOLATION => _$POLICY_VIOLATION;
  CodeEnum get RATE_LIMITED => _$RATE_LIMITED;
  CodeEnum get VERSION_CONFLICT => _$VERSION_CONFLICT;
  CodeEnum get SERVER_ERROR => _$SERVER_ERROR;
  CodeEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<CodeEnum> get values => _$values;
}

mixin _$CodeEnumMixin {
  // ignore: non_constant_identifier_names
  _$CodeEnumMeta get CodeEnum => const _$CodeEnumMeta();
}

Serializer<CodeEnum> _$codeEnumSerializer = _$CodeEnumSerializer();

class _$CodeEnumSerializer implements PrimitiveSerializer<CodeEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'AUTH_REQUIRED': 'AUTH_REQUIRED',
    'AUTH_FORBIDDEN_PROJECT': 'AUTH_FORBIDDEN_PROJECT',
    'VALIDATION_ERROR': 'VALIDATION_ERROR',
    'TASK_NOT_FOUND': 'TASK_NOT_FOUND',
    'TASK_STATE_CONFLICT': 'TASK_STATE_CONFLICT',
    'TASK_ALREADY_CLAIMED': 'TASK_ALREADY_CLAIMED',
    'LEASE_EXPIRED': 'LEASE_EXPIRED',
    'LEASE_NOT_OWNED': 'LEASE_NOT_OWNED',
    'DEPENDENCY_UNMET': 'DEPENDENCY_UNMET',
    'CONCURRENCY_LIMIT_REACHED': 'CONCURRENCY_LIMIT_REACHED',
    'SCOPE_VIOLATION': 'SCOPE_VIOLATION',
    'ROLE_NOT_PERMITTED': 'ROLE_NOT_PERMITTED',
    'AUDITOR_SAME_AS_CODER': 'AUDITOR_SAME_AS_CODER',
    'ATTACHMENT_NOT_READY': 'ATTACHMENT_NOT_READY',
    'ATTACHMENT_UNSUPPORTED_FORMAT': 'ATTACHMENT_UNSUPPORTED_FORMAT',
    'POLICY_VIOLATION': 'POLICY_VIOLATION',
    'RATE_LIMITED': 'RATE_LIMITED',
    'VERSION_CONFLICT': 'VERSION_CONFLICT',
    'SERVER_ERROR': 'SERVER_ERROR',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'AUTH_REQUIRED': 'AUTH_REQUIRED',
    'AUTH_FORBIDDEN_PROJECT': 'AUTH_FORBIDDEN_PROJECT',
    'VALIDATION_ERROR': 'VALIDATION_ERROR',
    'TASK_NOT_FOUND': 'TASK_NOT_FOUND',
    'TASK_STATE_CONFLICT': 'TASK_STATE_CONFLICT',
    'TASK_ALREADY_CLAIMED': 'TASK_ALREADY_CLAIMED',
    'LEASE_EXPIRED': 'LEASE_EXPIRED',
    'LEASE_NOT_OWNED': 'LEASE_NOT_OWNED',
    'DEPENDENCY_UNMET': 'DEPENDENCY_UNMET',
    'CONCURRENCY_LIMIT_REACHED': 'CONCURRENCY_LIMIT_REACHED',
    'SCOPE_VIOLATION': 'SCOPE_VIOLATION',
    'ROLE_NOT_PERMITTED': 'ROLE_NOT_PERMITTED',
    'AUDITOR_SAME_AS_CODER': 'AUDITOR_SAME_AS_CODER',
    'ATTACHMENT_NOT_READY': 'ATTACHMENT_NOT_READY',
    'ATTACHMENT_UNSUPPORTED_FORMAT': 'ATTACHMENT_UNSUPPORTED_FORMAT',
    'POLICY_VIOLATION': 'POLICY_VIOLATION',
    'RATE_LIMITED': 'RATE_LIMITED',
    'VERSION_CONFLICT': 'VERSION_CONFLICT',
    'SERVER_ERROR': 'SERVER_ERROR',
  };

  @override
  final Iterable<Type> types = const <Type>[CodeEnum];
  @override
  final String wireName = 'CodeEnum';

  @override
  Object serialize(Serializers serializers, CodeEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  CodeEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      CodeEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
