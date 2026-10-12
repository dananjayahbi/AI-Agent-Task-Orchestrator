// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'checkpoint_create.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$CheckpointCreate extends CheckpointCreate {
  @override
  final String sessionId;
  @override
  final int leaseGeneration;
  @override
  final String? message;
  @override
  final int? percent;
  @override
  final JsonObject? tokenUsage;
  @override
  final CheckpointCreateKindEnum? kind;

  factory _$CheckpointCreate(
          [void Function(CheckpointCreateBuilder)? updates]) =>
      (CheckpointCreateBuilder()..update(updates))._build();

  _$CheckpointCreate._(
      {required this.sessionId,
      required this.leaseGeneration,
      this.message,
      this.percent,
      this.tokenUsage,
      this.kind})
      : super._();
  @override
  CheckpointCreate rebuild(void Function(CheckpointCreateBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  CheckpointCreateBuilder toBuilder() =>
      CheckpointCreateBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is CheckpointCreate &&
        sessionId == other.sessionId &&
        leaseGeneration == other.leaseGeneration &&
        message == other.message &&
        percent == other.percent &&
        tokenUsage == other.tokenUsage &&
        kind == other.kind;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, sessionId.hashCode);
    _$hash = $jc(_$hash, leaseGeneration.hashCode);
    _$hash = $jc(_$hash, message.hashCode);
    _$hash = $jc(_$hash, percent.hashCode);
    _$hash = $jc(_$hash, tokenUsage.hashCode);
    _$hash = $jc(_$hash, kind.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'CheckpointCreate')
          ..add('sessionId', sessionId)
          ..add('leaseGeneration', leaseGeneration)
          ..add('message', message)
          ..add('percent', percent)
          ..add('tokenUsage', tokenUsage)
          ..add('kind', kind))
        .toString();
  }
}

class CheckpointCreateBuilder
    implements Builder<CheckpointCreate, CheckpointCreateBuilder> {
  _$CheckpointCreate? _$v;

  String? _sessionId;
  String? get sessionId => _$this._sessionId;
  set sessionId(String? sessionId) => _$this._sessionId = sessionId;

  int? _leaseGeneration;
  int? get leaseGeneration => _$this._leaseGeneration;
  set leaseGeneration(int? leaseGeneration) =>
      _$this._leaseGeneration = leaseGeneration;

  String? _message;
  String? get message => _$this._message;
  set message(String? message) => _$this._message = message;

  int? _percent;
  int? get percent => _$this._percent;
  set percent(int? percent) => _$this._percent = percent;

  JsonObject? _tokenUsage;
  JsonObject? get tokenUsage => _$this._tokenUsage;
  set tokenUsage(JsonObject? tokenUsage) => _$this._tokenUsage = tokenUsage;

  CheckpointCreateKindEnum? _kind;
  CheckpointCreateKindEnum? get kind => _$this._kind;
  set kind(CheckpointCreateKindEnum? kind) => _$this._kind = kind;

  CheckpointCreateBuilder() {
    CheckpointCreate._defaults(this);
  }

  CheckpointCreateBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _sessionId = $v.sessionId;
      _leaseGeneration = $v.leaseGeneration;
      _message = $v.message;
      _percent = $v.percent;
      _tokenUsage = $v.tokenUsage;
      _kind = $v.kind;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(CheckpointCreate other) {
    _$v = other as _$CheckpointCreate;
  }

  @override
  void update(void Function(CheckpointCreateBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  CheckpointCreate build() => _build();

  _$CheckpointCreate _build() {
    final _$result = _$v ??
        _$CheckpointCreate._(
          sessionId: BuiltValueNullFieldError.checkNotNull(
              sessionId, r'CheckpointCreate', 'sessionId'),
          leaseGeneration: BuiltValueNullFieldError.checkNotNull(
              leaseGeneration, r'CheckpointCreate', 'leaseGeneration'),
          message: message,
          percent: percent,
          tokenUsage: tokenUsage,
          kind: kind,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
