import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../review/review_repository.dart';
import 'push_payload.dart';

/// The pending notification tap (MT-5.9-01; Section 14.2 "after unlock").
///
/// A tap (OS notification tap on cold/warm start, later the in-app banner's
/// tap — MT-5.9-02) is recorded here and consumed by
/// `NotificationTapBinder` **only while the biometric gate is unlocked** —
/// the binder lives inside the gate's unlocked branch, so a tap that arrives
/// during `GateStatus.locked` sits in this provider until unlock makes the
/// binder mount (gate precedence over routing, Section 14.2; ADR-006).
class PendingNotificationTapNotifier extends Notifier<PushTapPayload?> {
  @override
  PushTapPayload? build() => null;

  /// Records one platform message as a tap to route. Returns false when the
  /// payload is not the MT-5.4-02 contract (malformed → route nowhere; the
  /// caller's honest no-op, never a guess).
  bool report(Map<String, String> data) {
    final PushTapPayload? payload = PushTapPayload.tryParse(data);
    if (payload == null) {
      return false;
    }
    arm(payload);
    return true;
  }

  /// Arms an already-parsed payload (the MT-5.9-02 banner tap, which holds
  /// the parsed payload and must route identically to an OS tap).
  void arm(PushTapPayload payload) {
    state = payload;
  }

  /// Consumed — the binder clears it before navigating so one tap routes once.
  void clear() {
    state = null;
  }
}

final NotifierProvider<PendingNotificationTapNotifier, PushTapPayload?>
    pendingNotificationTapProvider =
    NotifierProvider<PendingNotificationTapNotifier, PushTapPayload?>(
  PendingNotificationTapNotifier.new,
);

/// Where a resolved tap lands (Section 14.2's deep-link rule).
enum TapResolutionKind {
  /// The task is `in_human_review` — open its review sheet (the plan's
  /// acceptance: "notification tap lands on the correct review sheet").
  reviewSheet,

  /// The task no longer exists or is no longer awaiting review — the
  /// documented stale fallback (MT-5.9-01 risk note; choice recorded in the
  /// WP changelog): a clear explained state instead of a broken sheet.
  stale,

  /// The state could not be determined (transport/server failure) — an
  /// honest error state with retry, never a wrong destination.
  unreachable,
}

/// The outcome of resolving a tap's payload id against the server.
class TapResolution {
  const TapResolution.reviewSheet(this.taskId)
      : kind = TapResolutionKind.reviewSheet,
        error = null;

  const TapResolution.stale()
      : kind = TapResolutionKind.stale,
        taskId = null,
        error = null;

  const TapResolution.unreachable(this.error)
      : kind = TapResolutionKind.unreachable,
        taskId = null;

  final TapResolutionKind kind;

  /// Set only for [TapResolutionKind.reviewSheet].
  final String? taskId;

  /// Set only for [TapResolutionKind.unreachable].
  final OrchestratorApiException? error;
}

/// Post-unlock route resolution: fetch the task from the payload id, decide
/// the destination (MT-5.9-01 Scope: "fetch the task from the payload id
/// after unlock and open its review sheet").
class NotificationTapResolver {
  NotificationTapResolver(this._repository);

  final ReviewRepository _repository;

  Future<TapResolution> resolve(PushTapPayload payload) async {
    try {
      final Task task = await _repository.fetchTask(payload.taskId);
      if (task.state == StateEnum.inHumanReview) {
        return TapResolution.reviewSheet(payload.taskId);
      }
      return TapResolution.stale();
    } on OrchestratorApiException catch (error) {
      if (error.code == CodeEnum.TASK_NOT_FOUND) {
        // The id resolves to nothing — same user-facing fact as a task
        // that left review: not actionable, explained, no broken sheet.
        return TapResolution.stale();
      }
      return TapResolution.unreachable(error);
    }
  }
}

/// The resolver seam — tests inject a scripted repository behind
/// `reviewRepositoryProvider` (one seam, the review sheet's own).
final Provider<NotificationTapResolver> notificationTapResolverProvider =
    Provider<NotificationTapResolver>(
  (Ref ref) => NotificationTapResolver(ref.watch(reviewRepositoryProvider)),
);
