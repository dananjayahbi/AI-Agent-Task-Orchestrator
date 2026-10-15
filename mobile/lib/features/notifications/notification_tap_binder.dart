import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/routes.dart';
import 'foreground_banner.dart';
import 'notification_history.dart';
import 'notification_tap_router.dart';
import 'push_payload.dart';

/// Consumes pending notification taps **after unlock** (MT-5.9-01;
/// Section 14.2 "tapping a notification deep-links to the task's review
/// sheet *after unlock*").
///
/// Placed inside `LockGate`'s unlocked branch (see `OrchestratorApp`), so
/// the gate precedence is structural rather than checked: while the gate is
/// locked this widget is not in the tree, a recorded tap simply waits in
/// [pendingNotificationTapProvider], and the tap route cannot be pushed
/// (nothing navigates before biometric success — ADR-006). Once unlocked,
/// two paths consume:
///
/// * **cold start** — the binder mounts after the first unlock and consumes
///   whatever tap arrived during launch (post-frame check in `initState`);
/// * **warm start** — the binder is already mounted; a new tap triggers the
///   provider listener and routes immediately (freshly unlocked) or waits
///   for the next unlock (inactivity timeout had re-locked).
///
/// Navigation goes through the app-level [AppRoutes.navigatorKey] because
/// the binder sits *above* the navigator by construction.
class NotificationTapBinder extends ConsumerStatefulWidget {
  const NotificationTapBinder({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<NotificationTapBinder> createState() =>
      _NotificationTapBinderState();
}

class _NotificationTapBinderState extends ConsumerState<NotificationTapBinder> {
  @override
  void initState() {
    super.initState();
    // Cold-start path: a tap may already be pending when the unlocked tree
    // first mounts.
    WidgetsBinding.instance.addPostFrameCallback((_) => _consumeIfReady());
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<PushTapPayload?>(pendingNotificationTapProvider,
        (PushTapPayload? previous, PushTapPayload? next) {
      if (next != null) {
        _consumeIfReady();
      }
    });
    return widget.child;
  }

  void _consumeIfReady() {
    final PushTapPayload? pending = ref.read(pendingNotificationTapProvider);
    if (pending == null) {
      return;
    }
    final NavigatorState? navigator = AppRoutes.navigatorKey.currentState;
    if (navigator == null) {
      // The navigator is not mounted yet — leave the tap pending; the next
      // frame/listener retries rather than dropping the tap silently.
      return;
    }
    ref.read(pendingNotificationTapProvider.notifier).clear();
    // The tapped alert counts as presented (MT-5.9-02): the system-tap
    // receipt feeds MT-5.9-03's history and the key stops a later banner
    // for the same event. Recording is deduped against the banner's own
    // receipt and never blocks routing (fire-and-forget by design).
    ref.read(presentedPushKeysProvider.notifier).add(pending.dedupeKey);
    unawaited(
      ref
          .read(notificationHistoryProvider.notifier)
          .record(pending, origin: NotificationOrigin.systemNotification),
    );
    navigator.pushNamed(AppRoutes.notificationTap, arguments: pending);
  }
}
