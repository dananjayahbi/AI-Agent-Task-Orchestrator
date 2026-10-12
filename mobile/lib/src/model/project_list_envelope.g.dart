// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'project_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ProjectListEnvelope extends ProjectListEnvelope {
  @override
  final BuiltList<Project> results;
  @override
  final String? nextCursor;

  factory _$ProjectListEnvelope(
          [void Function(ProjectListEnvelopeBuilder)? updates]) =>
      (ProjectListEnvelopeBuilder()..update(updates))._build();

  _$ProjectListEnvelope._({required this.results, this.nextCursor}) : super._();
  @override
  ProjectListEnvelope rebuild(
          void Function(ProjectListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ProjectListEnvelopeBuilder toBuilder() =>
      ProjectListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ProjectListEnvelope &&
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
    return (newBuiltValueToStringHelper(r'ProjectListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class ProjectListEnvelopeBuilder
    implements Builder<ProjectListEnvelope, ProjectListEnvelopeBuilder> {
  _$ProjectListEnvelope? _$v;

  ListBuilder<Project>? _results;
  ListBuilder<Project> get results =>
      _$this._results ??= ListBuilder<Project>();
  set results(ListBuilder<Project>? results) => _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  ProjectListEnvelopeBuilder() {
    ProjectListEnvelope._defaults(this);
  }

  ProjectListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ProjectListEnvelope other) {
    _$v = other as _$ProjectListEnvelope;
  }

  @override
  void update(void Function(ProjectListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ProjectListEnvelope build() => _build();

  _$ProjectListEnvelope _build() {
    _$ProjectListEnvelope _$result;
    try {
      _$result = _$v ??
          _$ProjectListEnvelope._(
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
            r'ProjectListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
