// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'resolution_patch.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ResolutionPatch extends ResolutionPatch {
  @override
  final String resolutionId;
  @override
  final String kind;
  @override
  final String sha256;
  @override
  final int sizeBytes;
  @override
  final bool diffTooLarge;
  @override
  final String? patch_;
  @override
  final String? marker;

  factory _$ResolutionPatch([void Function(ResolutionPatchBuilder)? updates]) =>
      (ResolutionPatchBuilder()..update(updates))._build();

  _$ResolutionPatch._(
      {required this.resolutionId,
      required this.kind,
      required this.sha256,
      required this.sizeBytes,
      required this.diffTooLarge,
      this.patch_,
      this.marker})
      : super._();
  @override
  ResolutionPatch rebuild(void Function(ResolutionPatchBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ResolutionPatchBuilder toBuilder() => ResolutionPatchBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ResolutionPatch &&
        resolutionId == other.resolutionId &&
        kind == other.kind &&
        sha256 == other.sha256 &&
        sizeBytes == other.sizeBytes &&
        diffTooLarge == other.diffTooLarge &&
        patch_ == other.patch_ &&
        marker == other.marker;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, resolutionId.hashCode);
    _$hash = $jc(_$hash, kind.hashCode);
    _$hash = $jc(_$hash, sha256.hashCode);
    _$hash = $jc(_$hash, sizeBytes.hashCode);
    _$hash = $jc(_$hash, diffTooLarge.hashCode);
    _$hash = $jc(_$hash, patch_.hashCode);
    _$hash = $jc(_$hash, marker.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ResolutionPatch')
          ..add('resolutionId', resolutionId)
          ..add('kind', kind)
          ..add('sha256', sha256)
          ..add('sizeBytes', sizeBytes)
          ..add('diffTooLarge', diffTooLarge)
          ..add('patch_', patch_)
          ..add('marker', marker))
        .toString();
  }
}

class ResolutionPatchBuilder
    implements Builder<ResolutionPatch, ResolutionPatchBuilder> {
  _$ResolutionPatch? _$v;

  String? _resolutionId;
  String? get resolutionId => _$this._resolutionId;
  set resolutionId(String? resolutionId) => _$this._resolutionId = resolutionId;

  String? _kind;
  String? get kind => _$this._kind;
  set kind(String? kind) => _$this._kind = kind;

  String? _sha256;
  String? get sha256 => _$this._sha256;
  set sha256(String? sha256) => _$this._sha256 = sha256;

  int? _sizeBytes;
  int? get sizeBytes => _$this._sizeBytes;
  set sizeBytes(int? sizeBytes) => _$this._sizeBytes = sizeBytes;

  bool? _diffTooLarge;
  bool? get diffTooLarge => _$this._diffTooLarge;
  set diffTooLarge(bool? diffTooLarge) => _$this._diffTooLarge = diffTooLarge;

  String? _patch_;
  String? get patch_ => _$this._patch_;
  set patch_(String? patch_) => _$this._patch_ = patch_;

  String? _marker;
  String? get marker => _$this._marker;
  set marker(String? marker) => _$this._marker = marker;

  ResolutionPatchBuilder() {
    ResolutionPatch._defaults(this);
  }

  ResolutionPatchBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _resolutionId = $v.resolutionId;
      _kind = $v.kind;
      _sha256 = $v.sha256;
      _sizeBytes = $v.sizeBytes;
      _diffTooLarge = $v.diffTooLarge;
      _patch_ = $v.patch_;
      _marker = $v.marker;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ResolutionPatch other) {
    _$v = other as _$ResolutionPatch;
  }

  @override
  void update(void Function(ResolutionPatchBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ResolutionPatch build() => _build();

  _$ResolutionPatch _build() {
    final _$result = _$v ??
        _$ResolutionPatch._(
          resolutionId: BuiltValueNullFieldError.checkNotNull(
              resolutionId, r'ResolutionPatch', 'resolutionId'),
          kind: BuiltValueNullFieldError.checkNotNull(
              kind, r'ResolutionPatch', 'kind'),
          sha256: BuiltValueNullFieldError.checkNotNull(
              sha256, r'ResolutionPatch', 'sha256'),
          sizeBytes: BuiltValueNullFieldError.checkNotNull(
              sizeBytes, r'ResolutionPatch', 'sizeBytes'),
          diffTooLarge: BuiltValueNullFieldError.checkNotNull(
              diffTooLarge, r'ResolutionPatch', 'diffTooLarge'),
          patch_: patch_,
          marker: marker,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
