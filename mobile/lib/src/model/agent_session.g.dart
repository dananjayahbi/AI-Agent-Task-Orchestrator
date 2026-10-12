// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agent_session.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AgentSession extends AgentSession {
  @override
  final String id;
  @override
  final String projectId;
  @override
  final int tokenId;
  @override
  final String agentLabel;
  @override
  final String clientName;
  @override
  final CapabilityEnum capability;
  @override
  final TransportEnum transport;
  @override
  final DateTime startedAt;
  @override
  final DateTime lastSeenAt;
  @override
  final DateTime? endedAt;

  factory _$AgentSession([void Function(AgentSessionBuilder)? updates]) =>
      (AgentSessionBuilder()..update(updates))._build();

  _$AgentSession._(
      {required this.id,
      required this.projectId,
      required this.tokenId,
      required this.agentLabel,
      required this.clientName,
      required this.capability,
      required this.transport,
      required this.startedAt,
      required this.lastSeenAt,
      this.endedAt})
      : super._();
  @override
  AgentSession rebuild(void Function(AgentSessionBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AgentSessionBuilder toBuilder() => AgentSessionBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AgentSession &&
        id == other.id &&
        projectId == other.projectId &&
        tokenId == other.tokenId &&
        agentLabel == other.agentLabel &&
        clientName == other.clientName &&
        capability == other.capability &&
        transport == other.transport &&
        startedAt == other.startedAt &&
        lastSeenAt == other.lastSeenAt &&
        endedAt == other.endedAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, projectId.hashCode);
    _$hash = $jc(_$hash, tokenId.hashCode);
    _$hash = $jc(_$hash, agentLabel.hashCode);
    _$hash = $jc(_$hash, clientName.hashCode);
    _$hash = $jc(_$hash, capability.hashCode);
    _$hash = $jc(_$hash, transport.hashCode);
    _$hash = $jc(_$hash, startedAt.hashCode);
    _$hash = $jc(_$hash, lastSeenAt.hashCode);
    _$hash = $jc(_$hash, endedAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AgentSession')
          ..add('id', id)
          ..add('projectId', projectId)
          ..add('tokenId', tokenId)
          ..add('agentLabel', agentLabel)
          ..add('clientName', clientName)
          ..add('capability', capability)
          ..add('transport', transport)
          ..add('startedAt', startedAt)
          ..add('lastSeenAt', lastSeenAt)
          ..add('endedAt', endedAt))
        .toString();
  }
}

class AgentSessionBuilder
    implements Builder<AgentSession, AgentSessionBuilder> {
  _$AgentSession? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _projectId;
  String? get projectId => _$this._projectId;
  set projectId(String? projectId) => _$this._projectId = projectId;

  int? _tokenId;
  int? get tokenId => _$this._tokenId;
  set tokenId(int? tokenId) => _$this._tokenId = tokenId;

  String? _agentLabel;
  String? get agentLabel => _$this._agentLabel;
  set agentLabel(String? agentLabel) => _$this._agentLabel = agentLabel;

  String? _clientName;
  String? get clientName => _$this._clientName;
  set clientName(String? clientName) => _$this._clientName = clientName;

  CapabilityEnum? _capability;
  CapabilityEnum? get capability => _$this._capability;
  set capability(CapabilityEnum? capability) => _$this._capability = capability;

  TransportEnum? _transport;
  TransportEnum? get transport => _$this._transport;
  set transport(TransportEnum? transport) => _$this._transport = transport;

  DateTime? _startedAt;
  DateTime? get startedAt => _$this._startedAt;
  set startedAt(DateTime? startedAt) => _$this._startedAt = startedAt;

  DateTime? _lastSeenAt;
  DateTime? get lastSeenAt => _$this._lastSeenAt;
  set lastSeenAt(DateTime? lastSeenAt) => _$this._lastSeenAt = lastSeenAt;

  DateTime? _endedAt;
  DateTime? get endedAt => _$this._endedAt;
  set endedAt(DateTime? endedAt) => _$this._endedAt = endedAt;

  AgentSessionBuilder() {
    AgentSession._defaults(this);
  }

  AgentSessionBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _projectId = $v.projectId;
      _tokenId = $v.tokenId;
      _agentLabel = $v.agentLabel;
      _clientName = $v.clientName;
      _capability = $v.capability;
      _transport = $v.transport;
      _startedAt = $v.startedAt;
      _lastSeenAt = $v.lastSeenAt;
      _endedAt = $v.endedAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AgentSession other) {
    _$v = other as _$AgentSession;
  }

  @override
  void update(void Function(AgentSessionBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AgentSession build() => _build();

  _$AgentSession _build() {
    final _$result = _$v ??
        _$AgentSession._(
          id: BuiltValueNullFieldError.checkNotNull(id, r'AgentSession', 'id'),
          projectId: BuiltValueNullFieldError.checkNotNull(
              projectId, r'AgentSession', 'projectId'),
          tokenId: BuiltValueNullFieldError.checkNotNull(
              tokenId, r'AgentSession', 'tokenId'),
          agentLabel: BuiltValueNullFieldError.checkNotNull(
              agentLabel, r'AgentSession', 'agentLabel'),
          clientName: BuiltValueNullFieldError.checkNotNull(
              clientName, r'AgentSession', 'clientName'),
          capability: BuiltValueNullFieldError.checkNotNull(
              capability, r'AgentSession', 'capability'),
          transport: BuiltValueNullFieldError.checkNotNull(
              transport, r'AgentSession', 'transport'),
          startedAt: BuiltValueNullFieldError.checkNotNull(
              startedAt, r'AgentSession', 'startedAt'),
          lastSeenAt: BuiltValueNullFieldError.checkNotNull(
              lastSeenAt, r'AgentSession', 'lastSeenAt'),
          endedAt: endedAt,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
