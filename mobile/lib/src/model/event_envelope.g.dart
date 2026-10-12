// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'event_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$EventEnvelope extends EventEnvelope {
  @override
  final int id;
  @override
  final EventEnvelopeTypeEnum type;
  @override
  final String projectId;
  @override
  final String? taskId;
  @override
  final String occurredAt;
  @override
  final EventActor actor;
  @override
  final JsonObject? data;

  factory _$EventEnvelope([void Function(EventEnvelopeBuilder)? updates]) =>
      (EventEnvelopeBuilder()..update(updates))._build();

  _$EventEnvelope._(
      {required this.id,
      required this.type,
      required this.projectId,
      this.taskId,
      required this.occurredAt,
      required this.actor,
      this.data})
      : super._();
  @override
  EventEnvelope rebuild(void Function(EventEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  EventEnvelopeBuilder toBuilder() => EventEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is EventEnvelope &&
        id == other.id &&
        type == other.type &&
        projectId == other.projectId &&
        taskId == other.taskId &&
        occurredAt == other.occurredAt &&
        actor == other.actor &&
        data == other.data;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, type.hashCode);
    _$hash = $jc(_$hash, projectId.hashCode);
    _$hash = $jc(_$hash, taskId.hashCode);
    _$hash = $jc(_$hash, occurredAt.hashCode);
    _$hash = $jc(_$hash, actor.hashCode);
    _$hash = $jc(_$hash, data.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'EventEnvelope')
          ..add('id', id)
          ..add('type', type)
          ..add('projectId', projectId)
          ..add('taskId', taskId)
          ..add('occurredAt', occurredAt)
          ..add('actor', actor)
          ..add('data', data))
        .toString();
  }
}

class EventEnvelopeBuilder
    implements Builder<EventEnvelope, EventEnvelopeBuilder> {
  _$EventEnvelope? _$v;

  int? _id;
  int? get id => _$this._id;
  set id(int? id) => _$this._id = id;

  EventEnvelopeTypeEnum? _type;
  EventEnvelopeTypeEnum? get type => _$this._type;
  set type(EventEnvelopeTypeEnum? type) => _$this._type = type;

  String? _projectId;
  String? get projectId => _$this._projectId;
  set projectId(String? projectId) => _$this._projectId = projectId;

  String? _taskId;
  String? get taskId => _$this._taskId;
  set taskId(String? taskId) => _$this._taskId = taskId;

  String? _occurredAt;
  String? get occurredAt => _$this._occurredAt;
  set occurredAt(String? occurredAt) => _$this._occurredAt = occurredAt;

  EventActorBuilder? _actor;
  EventActorBuilder get actor => _$this._actor ??= EventActorBuilder();
  set actor(EventActorBuilder? actor) => _$this._actor = actor;

  JsonObject? _data;
  JsonObject? get data => _$this._data;
  set data(JsonObject? data) => _$this._data = data;

  EventEnvelopeBuilder() {
    EventEnvelope._defaults(this);
  }

  EventEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _type = $v.type;
      _projectId = $v.projectId;
      _taskId = $v.taskId;
      _occurredAt = $v.occurredAt;
      _actor = $v.actor.toBuilder();
      _data = $v.data;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(EventEnvelope other) {
    _$v = other as _$EventEnvelope;
  }

  @override
  void update(void Function(EventEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  EventEnvelope build() => _build();

  _$EventEnvelope _build() {
    _$EventEnvelope _$result;
    try {
      _$result = _$v ??
          _$EventEnvelope._(
            id: BuiltValueNullFieldError.checkNotNull(
                id, r'EventEnvelope', 'id'),
            type: BuiltValueNullFieldError.checkNotNull(
                type, r'EventEnvelope', 'type'),
            projectId: BuiltValueNullFieldError.checkNotNull(
                projectId, r'EventEnvelope', 'projectId'),
            taskId: taskId,
            occurredAt: BuiltValueNullFieldError.checkNotNull(
                occurredAt, r'EventEnvelope', 'occurredAt'),
            actor: actor.build(),
            data: data,
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'actor';
        actor.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'EventEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
