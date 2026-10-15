// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'notification_preference.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$NotificationPreference extends NotificationPreference {
  @override
  final EventTypeEnum eventType;
  @override
  final bool enabled;

  factory _$NotificationPreference(
          [void Function(NotificationPreferenceBuilder)? updates]) =>
      (NotificationPreferenceBuilder()..update(updates))._build();

  _$NotificationPreference._({required this.eventType, required this.enabled})
      : super._();
  @override
  NotificationPreference rebuild(
          void Function(NotificationPreferenceBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  NotificationPreferenceBuilder toBuilder() =>
      NotificationPreferenceBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is NotificationPreference &&
        eventType == other.eventType &&
        enabled == other.enabled;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, eventType.hashCode);
    _$hash = $jc(_$hash, enabled.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'NotificationPreference')
          ..add('eventType', eventType)
          ..add('enabled', enabled))
        .toString();
  }
}

class NotificationPreferenceBuilder
    implements Builder<NotificationPreference, NotificationPreferenceBuilder> {
  _$NotificationPreference? _$v;

  EventTypeEnum? _eventType;
  EventTypeEnum? get eventType => _$this._eventType;
  set eventType(EventTypeEnum? eventType) => _$this._eventType = eventType;

  bool? _enabled;
  bool? get enabled => _$this._enabled;
  set enabled(bool? enabled) => _$this._enabled = enabled;

  NotificationPreferenceBuilder() {
    NotificationPreference._defaults(this);
  }

  NotificationPreferenceBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _eventType = $v.eventType;
      _enabled = $v.enabled;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(NotificationPreference other) {
    _$v = other as _$NotificationPreference;
  }

  @override
  void update(void Function(NotificationPreferenceBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  NotificationPreference build() => _build();

  _$NotificationPreference _build() {
    final _$result = _$v ??
        _$NotificationPreference._(
          eventType: BuiltValueNullFieldError.checkNotNull(
              eventType, r'NotificationPreference', 'eventType'),
          enabled: BuiltValueNullFieldError.checkNotNull(
              enabled, r'NotificationPreference', 'enabled'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
