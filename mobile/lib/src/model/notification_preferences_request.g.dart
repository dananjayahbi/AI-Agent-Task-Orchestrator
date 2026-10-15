// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'notification_preferences_request.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$NotificationPreferencesRequest extends NotificationPreferencesRequest {
  @override
  final BuiltList<NotificationPreference> preferences;

  factory _$NotificationPreferencesRequest(
          [void Function(NotificationPreferencesRequestBuilder)? updates]) =>
      (NotificationPreferencesRequestBuilder()..update(updates))._build();

  _$NotificationPreferencesRequest._({required this.preferences}) : super._();
  @override
  NotificationPreferencesRequest rebuild(
          void Function(NotificationPreferencesRequestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  NotificationPreferencesRequestBuilder toBuilder() =>
      NotificationPreferencesRequestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is NotificationPreferencesRequest &&
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
    return (newBuiltValueToStringHelper(r'NotificationPreferencesRequest')
          ..add('preferences', preferences))
        .toString();
  }
}

class NotificationPreferencesRequestBuilder
    implements
        Builder<NotificationPreferencesRequest,
            NotificationPreferencesRequestBuilder> {
  _$NotificationPreferencesRequest? _$v;

  ListBuilder<NotificationPreference>? _preferences;
  ListBuilder<NotificationPreference> get preferences =>
      _$this._preferences ??= ListBuilder<NotificationPreference>();
  set preferences(ListBuilder<NotificationPreference>? preferences) =>
      _$this._preferences = preferences;

  NotificationPreferencesRequestBuilder() {
    NotificationPreferencesRequest._defaults(this);
  }

  NotificationPreferencesRequestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _preferences = $v.preferences.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(NotificationPreferencesRequest other) {
    _$v = other as _$NotificationPreferencesRequest;
  }

  @override
  void update(void Function(NotificationPreferencesRequestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  NotificationPreferencesRequest build() => _build();

  _$NotificationPreferencesRequest _build() {
    _$NotificationPreferencesRequest _$result;
    try {
      _$result = _$v ??
          _$NotificationPreferencesRequest._(
            preferences: preferences.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'preferences';
        preferences.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'NotificationPreferencesRequest', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
