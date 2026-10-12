// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agent_session_create.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$AgentSessionCreate extends AgentSessionCreate {
  @override
  final String id;
  @override
  final String? agentLabel;
  @override
  final String? clientName;
  @override
  final CapabilityEnum? capability;
  @override
  final TransportEnum transport;

  factory _$AgentSessionCreate(
          [void Function(AgentSessionCreateBuilder)? updates]) =>
      (AgentSessionCreateBuilder()..update(updates))._build();

  _$AgentSessionCreate._(
      {required this.id,
      this.agentLabel,
      this.clientName,
      this.capability,
      required this.transport})
      : super._();
  @override
  AgentSessionCreate rebuild(
          void Function(AgentSessionCreateBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  AgentSessionCreateBuilder toBuilder() =>
      AgentSessionCreateBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is AgentSessionCreate &&
        id == other.id &&
        agentLabel == other.agentLabel &&
        clientName == other.clientName &&
        capability == other.capability &&
        transport == other.transport;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, agentLabel.hashCode);
    _$hash = $jc(_$hash, clientName.hashCode);
    _$hash = $jc(_$hash, capability.hashCode);
    _$hash = $jc(_$hash, transport.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'AgentSessionCreate')
          ..add('id', id)
          ..add('agentLabel', agentLabel)
          ..add('clientName', clientName)
          ..add('capability', capability)
          ..add('transport', transport))
        .toString();
  }
}

class AgentSessionCreateBuilder
    implements Builder<AgentSessionCreate, AgentSessionCreateBuilder> {
  _$AgentSessionCreate? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

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

  AgentSessionCreateBuilder() {
    AgentSessionCreate._defaults(this);
  }

  AgentSessionCreateBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _agentLabel = $v.agentLabel;
      _clientName = $v.clientName;
      _capability = $v.capability;
      _transport = $v.transport;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(AgentSessionCreate other) {
    _$v = other as _$AgentSessionCreate;
  }

  @override
  void update(void Function(AgentSessionCreateBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  AgentSessionCreate build() => _build();

  _$AgentSessionCreate _build() {
    final _$result = _$v ??
        _$AgentSessionCreate._(
          id: BuiltValueNullFieldError.checkNotNull(
              id, r'AgentSessionCreate', 'id'),
          agentLabel: agentLabel,
          clientName: clientName,
          capability: capability,
          transport: BuiltValueNullFieldError.checkNotNull(
              transport, r'AgentSessionCreate', 'transport'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
