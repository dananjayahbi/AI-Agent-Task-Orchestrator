//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_element, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/model/merge_strategy_enum.dart';
import 'package:orchestrator_mobile/src/model/policy_preset_enum.dart';
import 'package:orchestrator_mobile/src/model/lease_extension_mode_enum.dart';
import 'package:built_value/built_value.dart';
import 'package:built_value/serializer.dart';

part 'patched_project_policy.g.dart';

/// The Section 7.2 policy table as a validated read/write contract.
///
/// Properties:
/// * [leaseDurationMinutes] - Lease length and per-checkpoint extension; default 45 (7.2).
/// * [leaseMaxTotalMinutes] - Hard cap on one continuous claim; default 240 (7.2). Must be >= lease_duration_minutes (MT-3.1-03 cross-field rule).
/// * [leaseExtensionMode] - checkpoint_only (default) or checkpoint_and_liveness (per-project option — OQ-04's recommended product default is unchanged; checkpoint_only is the enforced default, MT-3.1-01).  * `checkpoint_only` - checkpoint only * `checkpoint_and_liveness` - checkpoint and liveness
/// * [maxRetries] - Lease failures before escalation; default 3 (7.2).
/// * [maxConcurrentTasks] - Simultaneous in_progress tasks; default 1 (G-26). 0 is legal: it pauses claiming without touching active_status.
/// * [autonomousDiffThresholdLines] - Max changed lines for auto-complete; default 250 (7.2).
/// * [auditorMinConfidence] - Minimum auditor confidence, 1-5; default 4 (7.2).
/// * [criticalPathGlobs] - Escalating paths (CI/CD, root migrations, security config). Section 12.3 rules apply (MT-3.1-03): syntax-checked, repo-root-relative, no '..' traversal.
/// * [migrationPathGlobs] - Escalating framework-specific migration paths; Section 12.3 rules apply (MT-3.1-03).
/// * [sensitiveConfigGlobs] - Escalating env/key/security-rule paths; Section 12.3 rules apply (MT-3.1-03).
/// * [autoCompleteEnabled] - If false, every task goes to human review; default true (7.2).
/// * [mergeStrategy] - squash (default) / merge_commit / fast_forward_only (7.2).  * `squash` - squash * `merge_commit` - merge commit * `fast_forward_only` - fast forward only
/// * [branchPrefix] - Canonical branch-name prefix, `{PID}` resolved per project when names are derived (G-09; default `feat/{PID}-`). Changing it affects bridge branch naming from WP-2.x on.
/// * [auditRequiredDefault] - Default audit_required for new tasks; default true (7.2).
/// * [stalledAfterMinutes] - UI warning when no checkpoint arrives; default 20 (7.2).
/// * [policyPreset] - Apply a framework preset (WP-3.1): fills critical_path_globs, migration_path_globs and sensitive_config_globs in one action. Unknown ids are rejected; combining it with any explicit glob field in the same request is refused (no implicit ordering). Omitting it leaves the patched globs as sent.  * `django` - django * `nextjs` - nextjs * `flutter` - flutter
@BuiltValue()
abstract class PatchedProjectPolicy
    implements Built<PatchedProjectPolicy, PatchedProjectPolicyBuilder> {
  /// Lease length and per-checkpoint extension; default 45 (7.2).
  @BuiltValueField(wireName: r'lease_duration_minutes')
  int? get leaseDurationMinutes;

  /// Hard cap on one continuous claim; default 240 (7.2). Must be >= lease_duration_minutes (MT-3.1-03 cross-field rule).
  @BuiltValueField(wireName: r'lease_max_total_minutes')
  int? get leaseMaxTotalMinutes;

  /// checkpoint_only (default) or checkpoint_and_liveness (per-project option — OQ-04's recommended product default is unchanged; checkpoint_only is the enforced default, MT-3.1-01).  * `checkpoint_only` - checkpoint only * `checkpoint_and_liveness` - checkpoint and liveness
  @BuiltValueField(wireName: r'lease_extension_mode')
  LeaseExtensionModeEnum? get leaseExtensionMode;
  // enum leaseExtensionModeEnum {  checkpoint_only,  checkpoint_and_liveness,  };

  /// Lease failures before escalation; default 3 (7.2).
  @BuiltValueField(wireName: r'max_retries')
  int? get maxRetries;

  /// Simultaneous in_progress tasks; default 1 (G-26). 0 is legal: it pauses claiming without touching active_status.
  @BuiltValueField(wireName: r'max_concurrent_tasks')
  int? get maxConcurrentTasks;

  /// Max changed lines for auto-complete; default 250 (7.2).
  @BuiltValueField(wireName: r'autonomous_diff_threshold_lines')
  int? get autonomousDiffThresholdLines;

  /// Minimum auditor confidence, 1-5; default 4 (7.2).
  @BuiltValueField(wireName: r'auditor_min_confidence')
  int? get auditorMinConfidence;

  /// Escalating paths (CI/CD, root migrations, security config). Section 12.3 rules apply (MT-3.1-03): syntax-checked, repo-root-relative, no '..' traversal.
  @BuiltValueField(wireName: r'critical_path_globs')
  BuiltList<String>? get criticalPathGlobs;

  /// Escalating framework-specific migration paths; Section 12.3 rules apply (MT-3.1-03).
  @BuiltValueField(wireName: r'migration_path_globs')
  BuiltList<String>? get migrationPathGlobs;

  /// Escalating env/key/security-rule paths; Section 12.3 rules apply (MT-3.1-03).
  @BuiltValueField(wireName: r'sensitive_config_globs')
  BuiltList<String>? get sensitiveConfigGlobs;

  /// If false, every task goes to human review; default true (7.2).
  @BuiltValueField(wireName: r'auto_complete_enabled')
  bool? get autoCompleteEnabled;

  /// squash (default) / merge_commit / fast_forward_only (7.2).  * `squash` - squash * `merge_commit` - merge commit * `fast_forward_only` - fast forward only
  @BuiltValueField(wireName: r'merge_strategy')
  MergeStrategyEnum? get mergeStrategy;
  // enum mergeStrategyEnum {  squash,  merge_commit,  fast_forward_only,  };

  /// Canonical branch-name prefix, `{PID}` resolved per project when names are derived (G-09; default `feat/{PID}-`). Changing it affects bridge branch naming from WP-2.x on.
  @BuiltValueField(wireName: r'branch_prefix')
  String? get branchPrefix;

  /// Default audit_required for new tasks; default true (7.2).
  @BuiltValueField(wireName: r'audit_required_default')
  bool? get auditRequiredDefault;

  /// UI warning when no checkpoint arrives; default 20 (7.2).
  @BuiltValueField(wireName: r'stalled_after_minutes')
  int? get stalledAfterMinutes;

  /// Apply a framework preset (WP-3.1): fills critical_path_globs, migration_path_globs and sensitive_config_globs in one action. Unknown ids are rejected; combining it with any explicit glob field in the same request is refused (no implicit ordering). Omitting it leaves the patched globs as sent.  * `django` - django * `nextjs` - nextjs * `flutter` - flutter
  @BuiltValueField(wireName: r'policy_preset')
  PolicyPresetEnum? get policyPreset;
  // enum policyPresetEnum {  django,  nextjs,  flutter,  };

  PatchedProjectPolicy._();

  factory PatchedProjectPolicy([void updates(PatchedProjectPolicyBuilder b)]) =
      _$PatchedProjectPolicy;

  @BuiltValueHook(initializeBuilder: true)
  static void _defaults(PatchedProjectPolicyBuilder b) => b;

  @BuiltValueSerializer(custom: true)
  static Serializer<PatchedProjectPolicy> get serializer =>
      _$PatchedProjectPolicySerializer();
}

class _$PatchedProjectPolicySerializer
    implements PrimitiveSerializer<PatchedProjectPolicy> {
  @override
  final Iterable<Type> types = const [
    PatchedProjectPolicy,
    _$PatchedProjectPolicy
  ];

  @override
  final String wireName = r'PatchedProjectPolicy';

  Iterable<Object?> _serializeProperties(
    Serializers serializers,
    PatchedProjectPolicy object, {
    FullType specifiedType = FullType.unspecified,
  }) sync* {
    if (object.leaseDurationMinutes != null) {
      yield r'lease_duration_minutes';
      yield serializers.serialize(
        object.leaseDurationMinutes,
        specifiedType: const FullType(int),
      );
    }
    if (object.leaseMaxTotalMinutes != null) {
      yield r'lease_max_total_minutes';
      yield serializers.serialize(
        object.leaseMaxTotalMinutes,
        specifiedType: const FullType(int),
      );
    }
    if (object.leaseExtensionMode != null) {
      yield r'lease_extension_mode';
      yield serializers.serialize(
        object.leaseExtensionMode,
        specifiedType: const FullType(LeaseExtensionModeEnum),
      );
    }
    if (object.maxRetries != null) {
      yield r'max_retries';
      yield serializers.serialize(
        object.maxRetries,
        specifiedType: const FullType(int),
      );
    }
    if (object.maxConcurrentTasks != null) {
      yield r'max_concurrent_tasks';
      yield serializers.serialize(
        object.maxConcurrentTasks,
        specifiedType: const FullType(int),
      );
    }
    if (object.autonomousDiffThresholdLines != null) {
      yield r'autonomous_diff_threshold_lines';
      yield serializers.serialize(
        object.autonomousDiffThresholdLines,
        specifiedType: const FullType(int),
      );
    }
    if (object.auditorMinConfidence != null) {
      yield r'auditor_min_confidence';
      yield serializers.serialize(
        object.auditorMinConfidence,
        specifiedType: const FullType(int),
      );
    }
    if (object.criticalPathGlobs != null) {
      yield r'critical_path_globs';
      yield serializers.serialize(
        object.criticalPathGlobs,
        specifiedType: const FullType(BuiltList, [FullType(String)]),
      );
    }
    if (object.migrationPathGlobs != null) {
      yield r'migration_path_globs';
      yield serializers.serialize(
        object.migrationPathGlobs,
        specifiedType: const FullType(BuiltList, [FullType(String)]),
      );
    }
    if (object.sensitiveConfigGlobs != null) {
      yield r'sensitive_config_globs';
      yield serializers.serialize(
        object.sensitiveConfigGlobs,
        specifiedType: const FullType(BuiltList, [FullType(String)]),
      );
    }
    if (object.autoCompleteEnabled != null) {
      yield r'auto_complete_enabled';
      yield serializers.serialize(
        object.autoCompleteEnabled,
        specifiedType: const FullType(bool),
      );
    }
    if (object.mergeStrategy != null) {
      yield r'merge_strategy';
      yield serializers.serialize(
        object.mergeStrategy,
        specifiedType: const FullType(MergeStrategyEnum),
      );
    }
    if (object.branchPrefix != null) {
      yield r'branch_prefix';
      yield serializers.serialize(
        object.branchPrefix,
        specifiedType: const FullType(String),
      );
    }
    if (object.auditRequiredDefault != null) {
      yield r'audit_required_default';
      yield serializers.serialize(
        object.auditRequiredDefault,
        specifiedType: const FullType(bool),
      );
    }
    if (object.stalledAfterMinutes != null) {
      yield r'stalled_after_minutes';
      yield serializers.serialize(
        object.stalledAfterMinutes,
        specifiedType: const FullType(int),
      );
    }
    if (object.policyPreset != null) {
      yield r'policy_preset';
      yield serializers.serialize(
        object.policyPreset,
        specifiedType: const FullType(PolicyPresetEnum),
      );
    }
  }

  @override
  Object serialize(
    Serializers serializers,
    PatchedProjectPolicy object, {
    FullType specifiedType = FullType.unspecified,
  }) {
    return _serializeProperties(serializers, object,
            specifiedType: specifiedType)
        .toList();
  }

  void _deserializeProperties(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
    required List<Object?> serializedList,
    required PatchedProjectPolicyBuilder result,
    required List<Object?> unhandled,
  }) {
    for (var i = 0; i < serializedList.length; i += 2) {
      final key = serializedList[i] as String;
      final value = serializedList[i + 1];
      switch (key) {
        case r'lease_duration_minutes':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.leaseDurationMinutes = valueDes;
          break;
        case r'lease_max_total_minutes':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.leaseMaxTotalMinutes = valueDes;
          break;
        case r'lease_extension_mode':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(LeaseExtensionModeEnum),
          ) as LeaseExtensionModeEnum?;
          if (valueDes == null) continue;
          result.leaseExtensionMode = valueDes;
          break;
        case r'max_retries':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.maxRetries = valueDes;
          break;
        case r'max_concurrent_tasks':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.maxConcurrentTasks = valueDes;
          break;
        case r'autonomous_diff_threshold_lines':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.autonomousDiffThresholdLines = valueDes;
          break;
        case r'auditor_min_confidence':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.auditorMinConfidence = valueDes;
          break;
        case r'critical_path_globs':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.criticalPathGlobs.replace(valueDes);
          break;
        case r'migration_path_globs':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.migrationPathGlobs.replace(valueDes);
          break;
        case r'sensitive_config_globs':
          final valueDes = serializers.deserialize(
            value,
            specifiedType:
                const FullType.nullable(BuiltList, [FullType(String)]),
          ) as BuiltList<String>?;
          if (valueDes == null) continue;
          result.sensitiveConfigGlobs.replace(valueDes);
          break;
        case r'auto_complete_enabled':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(bool),
          ) as bool?;
          if (valueDes == null) continue;
          result.autoCompleteEnabled = valueDes;
          break;
        case r'merge_strategy':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(MergeStrategyEnum),
          ) as MergeStrategyEnum?;
          if (valueDes == null) continue;
          result.mergeStrategy = valueDes;
          break;
        case r'branch_prefix':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(String),
          ) as String?;
          if (valueDes == null) continue;
          result.branchPrefix = valueDes;
          break;
        case r'audit_required_default':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(bool),
          ) as bool?;
          if (valueDes == null) continue;
          result.auditRequiredDefault = valueDes;
          break;
        case r'stalled_after_minutes':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(int),
          ) as int?;
          if (valueDes == null) continue;
          result.stalledAfterMinutes = valueDes;
          break;
        case r'policy_preset':
          final valueDes = serializers.deserialize(
            value,
            specifiedType: const FullType.nullable(PolicyPresetEnum),
          ) as PolicyPresetEnum?;
          if (valueDes == null) continue;
          result.policyPreset = valueDes;
          break;
        default:
          unhandled.add(key);
          unhandled.add(value);
          break;
      }
    }
  }

  @override
  PatchedProjectPolicy deserialize(
    Serializers serializers,
    Object serialized, {
    FullType specifiedType = FullType.unspecified,
  }) {
    final result = PatchedProjectPolicyBuilder();
    final serializedList = (serialized as Iterable<Object?>).toList();
    final unhandled = <Object?>[];
    _deserializeProperties(
      serializers,
      serialized,
      specifiedType: specifiedType,
      serializedList: serializedList,
      unhandled: unhandled,
      result: result,
    );
    return result.build();
  }
}
