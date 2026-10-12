// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'claim_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ClaimResponse extends ClaimResponse {
  @override
  final Task task;
  @override
  final LeaseRecord lease;
  @override
  final RulesBlock rulesBlock;

  factory _$ClaimResponse([void Function(ClaimResponseBuilder)? updates]) =>
      (ClaimResponseBuilder()..update(updates))._build();

  _$ClaimResponse._(
      {required this.task, required this.lease, required this.rulesBlock})
      : super._();
  @override
  ClaimResponse rebuild(void Function(ClaimResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ClaimResponseBuilder toBuilder() => ClaimResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ClaimResponse &&
        task == other.task &&
        lease == other.lease &&
        rulesBlock == other.rulesBlock;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, task.hashCode);
    _$hash = $jc(_$hash, lease.hashCode);
    _$hash = $jc(_$hash, rulesBlock.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ClaimResponse')
          ..add('task', task)
          ..add('lease', lease)
          ..add('rulesBlock', rulesBlock))
        .toString();
  }
}

class ClaimResponseBuilder
    implements Builder<ClaimResponse, ClaimResponseBuilder> {
  _$ClaimResponse? _$v;

  TaskBuilder? _task;
  TaskBuilder get task => _$this._task ??= TaskBuilder();
  set task(TaskBuilder? task) => _$this._task = task;

  LeaseRecordBuilder? _lease;
  LeaseRecordBuilder get lease => _$this._lease ??= LeaseRecordBuilder();
  set lease(LeaseRecordBuilder? lease) => _$this._lease = lease;

  RulesBlockBuilder? _rulesBlock;
  RulesBlockBuilder get rulesBlock =>
      _$this._rulesBlock ??= RulesBlockBuilder();
  set rulesBlock(RulesBlockBuilder? rulesBlock) =>
      _$this._rulesBlock = rulesBlock;

  ClaimResponseBuilder() {
    ClaimResponse._defaults(this);
  }

  ClaimResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _task = $v.task.toBuilder();
      _lease = $v.lease.toBuilder();
      _rulesBlock = $v.rulesBlock.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ClaimResponse other) {
    _$v = other as _$ClaimResponse;
  }

  @override
  void update(void Function(ClaimResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ClaimResponse build() => _build();

  _$ClaimResponse _build() {
    _$ClaimResponse _$result;
    try {
      _$result = _$v ??
          _$ClaimResponse._(
            task: task.build(),
            lease: lease.build(),
            rulesBlock: rulesBlock.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'task';
        task.build();
        _$failedField = 'lease';
        lease.build();
        _$failedField = 'rulesBlock';
        rulesBlock.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'ClaimResponse', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
