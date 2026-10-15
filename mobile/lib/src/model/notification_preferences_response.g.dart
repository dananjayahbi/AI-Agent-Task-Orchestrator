// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'notification_preferences_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$NotificationPreferencesResponse
    extends NotificationPreferencesResponse {
  @override
  final BuiltList<NotificationPreference> preferences;

  factory _$NotificationPreferencesResponse(
          [void Function(NotificationPreferencesResponseBuilder)? updates]) =>
      (NotificationPreferencesResponseBuilder()..update(updates))._build();

  _$NotificationPreferencesResponse._({required this.preferences}) : super._();
  @override
  NotificationPreferencesResponse rebuild(
          void Function(NotificationPreferencesResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  NotificationPreferencesResponseBuilder toBuilder() =>
      NotificationPreferencesResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is NotificationPreferencesResponse &&
        preferences == other.preferences;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, preferences.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'NotificationPreferencesResponse')
          ..add('preferences', preferences))
        .toString();
  }
}

class NotificationPreferencesResponseBuilder
    implements
        Builder<NotificationPreferencesResponse,
            NotificationPreferencesResponseBuilder> {
  _$NotificationPreferencesResponse? _$v;

  ListBuilder<NotificationPreference>? _preferences;
  ListBuilder<NotificationPreference> get preferences =>
      _$this._preferences ??= ListBuilder<NotificationPreference>();
  set preferences(ListBuilder<NotificationPreference>? preferences) =>
      _$this._preferences = preferences;

  NotificationPreferencesResponseBuilder() {
    NotificationPreferencesResponse._defaults(this);
  }

  NotificationPreferencesResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _preferences = $v.preferences.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(NotificationPreferencesResponse other) {
    _$v = other as _$NotificationPreferencesResponse;
  }

  @override
  void update(void Function(NotificationPreferencesResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  NotificationPreferencesResponse build() => _build();

  _$NotificationPreferencesResponse _build() {
    _$NotificationPreferencesResponse _$result;
    try {
      _$result = _$v ??
          _$NotificationPreferencesResponse._(
            preferences: preferences.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'preferences';
        preferences.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'NotificationPreferencesResponse', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
