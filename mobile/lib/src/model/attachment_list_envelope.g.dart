// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'attachment_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AttachmentListEnvelope extends AttachmentListEnvelope {
  @override
  final BuiltList<Attachment> results;
  @override
  final String? nextCursor;

  factory _$AttachmentListEnvelope(
          [void Function(AttachmentListEnvelopeBuilder)? updates]) =>
      (AttachmentListEnvelopeBuilder()..update(updates))._build();

  _$AttachmentListEnvelope._({required this.results, this.nextCursor})
      : super._();
  @override
  AttachmentListEnvelope rebuild(
          void Function(AttachmentListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AttachmentListEnvelopeBuilder toBuilder() =>
      AttachmentListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AttachmentListEnvelope &&
        results == other.results &&
        nextCursor == other.nextCursor;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, results.hashCode);
    _$hash = $jc(_$hash, nextCursor.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AttachmentListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class AttachmentListEnvelopeBuilder
    implements Builder<AttachmentListEnvelope, AttachmentListEnvelopeBuilder> {
  _$AttachmentListEnvelope? _$v;

  ListBuilder<Attachment>? _results;
  ListBuilder<Attachment> get results =>
      _$this._results ??= ListBuilder<Attachment>();
  set results(ListBuilder<Attachment>? results) => _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  AttachmentListEnvelopeBuilder() {
    AttachmentListEnvelope._defaults(this);
  }

  AttachmentListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AttachmentListEnvelope other) {
    _$v = other as _$AttachmentListEnvelope;
  }

  @override
  void update(void Function(AttachmentListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AttachmentListEnvelope build() => _build();

  _$AttachmentListEnvelope _build() {
    _$AttachmentListEnvelope _$result;
    try {
      _$result = _$v ??
          _$AttachmentListEnvelope._(
            results: results.build(),
            nextCursor: nextCursor,
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'results';
        results.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'AttachmentListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
