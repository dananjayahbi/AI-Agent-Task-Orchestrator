// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'merge_queue_item.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$MergeQueueItem extends MergeQueueItem {
  @override
  final String id;
  @override
  final String projectId;
  @override
  final String title;
  @override
  final String state;
  @override
  final int version;
  @override
  final String mergeStatus;
  @override
  final String? branchName;
  @override
  final String mergeStrategy;

  factory _$MergeQueueItem([void Function(MergeQueueItemBuilder)? updates]) =>
      (MergeQueueItemBuilder()..update(updates))._build();

  _$MergeQueueItem._(
      {required this.id,
      required this.projectId,
      required this.title,
      required this.state,
      required this.version,
      required this.mergeStatus,
      this.branchName,
      required this.mergeStrategy})
      : super._();
  @override
  MergeQueueItem rebuild(void Function(MergeQueueItemBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  MergeQueueItemBuilder toBuilder() => MergeQueueItemBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is MergeQueueItem &&
        id == other.id &&
        projectId == other.projectId &&
        title == other.title &&
        state == other.state &&
        version == other.version &&
        mergeStatus == other.mergeStatus &&
        branchName == other.branchName &&
        mergeStrategy == other.mergeStrategy;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, projectId.hashCode);
    _$hash = $jc(_$hash, title.hashCode);
    _$hash = $jc(_$hash, state.hashCode);
    _$hash = $jc(_$hash, version.hashCode);
    _$hash = $jc(_$hash, mergeStatus.hashCode);
    _$hash = $jc(_$hash, branchName.hashCode);
    _$hash = $jc(_$hash, mergeStrategy.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'MergeQueueItem')
          ..add('id', id)
          ..add('projectId', projectId)
          ..add('title', title)
          ..add('state', state)
          ..add('version', version)
          ..add('mergeStatus', mergeStatus)
          ..add('branchName', branchName)
          ..add('mergeStrategy', mergeStrategy))
        .toString();
  }
}

class MergeQueueItemBuilder
    implements Builder<MergeQueueItem, MergeQueueItemBuilder> {
  _$MergeQueueItem? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _projectId;
  String? get projectId => _$this._projectId;
  set projectId(String? projectId) => _$this._projectId = projectId;

  String? _title;
  String? get title => _$this._title;
  set title(String? title) => _$this._title = title;

  String? _state;
  String? get state => _$this._state;
  set state(String? state) => _$this._state = state;

  int? _version;
  int? get version => _$this._version;
  set version(int? version) => _$this._version = version;

  String? _mergeStatus;
  String? get mergeStatus => _$this._mergeStatus;
  set mergeStatus(String? mergeStatus) => _$this._mergeStatus = mergeStatus;

  String? _branchName;
  String? get branchName => _$this._branchName;
  set branchName(String? branchName) => _$this._branchName = branchName;

  String? _mergeStrategy;
  String? get mergeStrategy => _$this._mergeStrategy;
  set mergeStrategy(String? mergeStrategy) =>
      _$this._mergeStrategy = mergeStrategy;

  MergeQueueItemBuilder() {
    MergeQueueItem._defaults(this);
  }

  MergeQueueItemBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _projectId = $v.projectId;
      _title = $v.title;
      _state = $v.state;
      _version = $v.version;
      _mergeStatus = $v.mergeStatus;
      _branchName = $v.branchName;
      _mergeStrategy = $v.mergeStrategy;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(MergeQueueItem other) {
    _$v = other as _$MergeQueueItem;
  }

  @override
  void update(void Function(MergeQueueItemBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  MergeQueueItem build() => _build();

  _$MergeQueueItem _build() {
    final _$result = _$v ??
        _$MergeQueueItem._(
          id: BuiltValueNullFieldError.checkNotNull(
              id, r'MergeQueueItem', 'id'),
          projectId: BuiltValueNullFieldError.checkNotNull(
              projectId, r'MergeQueueItem', 'projectId'),
          title: BuiltValueNullFieldError.checkNotNull(
              title, r'MergeQueueItem', 'title'),
          state: BuiltValueNullFieldError.checkNotNull(
              state, r'MergeQueueItem', 'state'),
          version: BuiltValueNullFieldError.checkNotNull(
              version, r'MergeQueueItem', 'version'),
          mergeStatus: BuiltValueNullFieldError.checkNotNull(
              mergeStatus, r'MergeQueueItem', 'mergeStatus'),
          branchName: branchName,
          mergeStrategy: BuiltValueNullFieldError.checkNotNull(
              mergeStrategy, r'MergeQueueItem', 'mergeStrategy'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
