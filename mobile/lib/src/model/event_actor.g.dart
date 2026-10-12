// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'event_actor.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$EventActor extends EventActor {
  @override
  final EventActorTypeEnum type;
  @override
  final String ref;

  factory _$EventActor([void Function(EventActorBuilder)? updates]) =>
      (EventActorBuilder()..update(updates))._build();

  _$EventActor._({required this.type, required this.ref}) : super._();
  @override
  EventActor rebuild(void Function(EventActorBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  EventActorBuilder toBuilder() => EventActorBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is EventActor && type == other.type && ref == other.ref;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, type.hashCode);
    _$hash = $jc(_$hash, ref.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'EventActor')
          ..add('type', type)
          ..add('ref', ref))
        .toString();
  }
}

class EventActorBuilder implements Builder<EventActor, EventActorBuilder> {
  _$EventActor? _$v;

  EventActorTypeEnum? _type;
  EventActorTypeEnum? get type => _$this._type;
  set type(EventActorTypeEnum? type) => _$this._type = type;

  String? _ref;
  String? get ref => _$this._ref;
  set ref(String? ref) => _$this._ref = ref;

  EventActorBuilder() {
    EventActor._defaults(this);
  }

  EventActorBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _type = $v.type;
      _ref = $v.ref;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(EventActor other) {
    _$v = other as _$EventActor;
  }

  @override
  void update(void Function(EventActorBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  EventActor build() => _build();

  _$EventActor _build() {
    final _$result = _$v ??
        _$EventActor._(
          type: BuiltValueNullFieldError.checkNotNull(
              type, r'EventActor', 'type'),
          ref: BuiltValueNullFieldError.checkNotNull(ref, r'EventActor', 'ref'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
