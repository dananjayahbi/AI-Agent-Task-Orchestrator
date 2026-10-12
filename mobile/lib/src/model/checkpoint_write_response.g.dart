// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'checkpoint_write_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$CheckpointWriteResponse extends CheckpointWriteResponse {
  @override
  final Checkpoint checkpoint;
  @override
  final bool leaseExtended;
  @override
  final DateTime? leaseExpiresAt;
  @override
  final bool capped;

  factory _$CheckpointWriteResponse(
          [void Function(CheckpointWriteResponseBuilder)? updates]) =>
      (CheckpointWriteResponseBuilder()..update(updates))._build();

  _$CheckpointWriteResponse._(
      {required this.checkpoint,
      required this.leaseExtended,
      this.leaseExpiresAt,
      required this.capped})
      : super._();
  @override
  CheckpointWriteResponse rebuild(
          void Function(CheckpointWriteResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  CheckpointWriteResponseBuilder toBuilder() =>
      CheckpointWriteResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is CheckpointWriteResponse &&
        checkpoint == other.checkpoint &&
        leaseExtended == other.leaseExtended &&
        leaseExpiresAt == other.leaseExpiresAt &&
        capped == other.capped;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, checkpoint.hashCode);
    _$hash = $jc(_$hash, leaseExtended.hashCode);
    _$hash = $jc(_$hash, leaseExpiresAt.hashCode);
    _$hash = $jc(_$hash, capped.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'CheckpointWriteResponse')
          ..add('checkpoint', checkpoint)
          ..add('leaseExtended', leaseExtended)
          ..add('leaseExpiresAt', leaseExpiresAt)
          ..add('capped', capped))
        .toString();
  }
}

class CheckpointWriteResponseBuilder
    implements
        Builder<CheckpointWriteResponse, CheckpointWriteResponseBuilder> {
  _$CheckpointWriteResponse? _$v;

  CheckpointBuilder? _checkpoint;
  CheckpointBuilder get checkpoint =>
      _$this._checkpoint ??= CheckpointBuilder();
  set checkpoint(CheckpointBuilder? checkpoint) =>
      _$this._checkpoint = checkpoint;

  bool? _leaseExtended;
  bool? get leaseExtended => _$this._leaseExtended;
  set leaseExtended(bool? leaseExtended) =>
      _$this._leaseExtended = leaseExtended;

  DateTime? _leaseExpiresAt;
  DateTime? get leaseExpiresAt => _$this._leaseExpiresAt;
  set leaseExpiresAt(DateTime? leaseExpiresAt) =>
      _$this._leaseExpiresAt = leaseExpiresAt;

  bool? _capped;
  bool? get capped => _$this._capped;
  set capped(bool? capped) => _$this._capped = capped;

  CheckpointWriteResponseBuilder() {
    CheckpointWriteResponse._defaults(this);
  }

  CheckpointWriteResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _checkpoint = $v.checkpoint.toBuilder();
      _leaseExtended = $v.leaseExtended;
      _leaseExpiresAt = $v.leaseExpiresAt;
      _capped = $v.capped;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(CheckpointWriteResponse other) {
    _$v = other as _$CheckpointWriteResponse;
  }

  @override
  void update(void Function(CheckpointWriteResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  CheckpointWriteResponse build() => _build();

  _$CheckpointWriteResponse _build() {
    _$CheckpointWriteResponse _$result;
    try {
      _$result = _$v ??
          _$CheckpointWriteResponse._(
            checkpoint: checkpoint.build(),
            leaseExtended: BuiltValueNullFieldError.checkNotNull(
                leaseExtended, r'CheckpointWriteResponse', 'leaseExtended'),
            leaseExpiresAt: leaseExpiresAt,
            capped: BuiltValueNullFieldError.checkNotNull(
                capped, r'CheckpointWriteResponse', 'capped'),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'checkpoint';
        checkpoint.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'CheckpointWriteResponse', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
