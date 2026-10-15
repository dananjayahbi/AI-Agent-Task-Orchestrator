import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/routes.dart';
import '../../core/security/auth_gate.dart';
import 'notification_history.dart';
import 'notification_tap_router.dart';
import 'push_payload.dart';

/// The in-app banner's dismissal rule (MT-5.9-02 risk note — the plan
/// specifies none, so the recorded choice is: **tap to act or auto-dismiss
/// after a short delay; no explicit dismiss button** — the least intrusive
/// option that still guarantees the banner never wedges over the board).
const Duration foregroundBannerDuration = Duration(seconds: 6);

/// The banner currently displayed (null: none). The host widget renders it
/// as an overlay strip; clearing it is how dismissal happens.
final StateProvider<PushTapPayload?> activeBannerProvider =
    StateProvider<PushTapPayload?>((Ref ref) => null);

/// MT-5.4-03 dedupe keys this app already presented (banner *or* system
/// tap) — the app-side half of "a message already presented does not render
/// twice" (session-scoped: a restart cannot replay an OS tap as a banner).
class PresentedPushKeysNotifier extends Notifier<Set<String>> {
  @override
  Set<String> build() => <String>{};

  void add(String key) => state = <String>{...state, key};

  bool contains(String key) => state.contains(key);
}

final NotifierProvider<PresentedPushKeysNotifier, Set<String>>
    presentedPushKeysProvider =
    NotifierProvider<PresentedPushKeysNotifier, Set<String>>(
  PresentedPushKeysNotifier.new,
);

/// The foreground message entry seam (Section 14.2: "Foreground messages
/// display an in-app banner") — what the platform FCM foreground callback
/// will call when the transport lands.
///
/// In order, exactly once per message:
/// 1. the MT-5.4-02 payload contract must parse (else honest no-op);
/// 2. **gate check** — while locked nothing is presented and no sensitive
///    content renders (Section 14.2; the host widget additionally only
///    exists inside the unlocked branch);
/// 3. **dedupe** — a key already presented never renders again;
/// 4. the alert is recorded for MT-5.9-03's history, then the banner
///    becomes active for the host to display.
class ForegroundPushHandler extends Notifier<void> {
  @override
  void build() {}

  bool present(Map<String, String> data) {
    final PushTapPayload? payload = PushTapPayload.tryParse(data);
    if (payload == null) {
      return false;
    }
    if (ref.read(authGateProvider).status != GateStatus.unlocked) {
      // Locked: the minimal payload is the only protection and this app
      // chooses to show nothing at all until unlock (recorded decision).
      return false;
    }
    if (ref.read(presentedPushKeysProvider).contains(payload.dedupeKey)) {
      return false;
    }
    ref.read(presentedPushKeysProvider.notifier).add(payload.dedupeKey);
    // Recording is side material: it never gates or fails presentation.
    unawaited(
      ref
          .read(notificationHistoryProvider.notifier)
          .record(payload, origin: NotificationOrigin.banner),
    );
    ref.read(activeBannerProvider.notifier).state = payload;
    return true;
  }
}

final NotifierProvider<ForegroundPushHandler, void>
    foregroundPushHandlerProvider =
    NotifierProvider<ForegroundPushHandler, void>(ForegroundPushHandler.new);

/// Mounts the banner over the navigator while the gate is unlocked (placed
/// inside `LockGate`'s unlocked branch in `OrchestratorApp`) and owns the
/// dismissal rule: tap routes through MT-5.9-01's pending-tap seam, the
/// auto-dismiss timer clears an untouched banner.
class ForegroundBannerHost extends ConsumerStatefulWidget {
  const ForegroundBannerHost({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<ForegroundBannerHost> createState() =>
      _ForegroundBannerHostState();
}

class _ForegroundBannerHostState extends ConsumerState<ForegroundBannerHost> {
  OverlayEntry? _entry;
  Timer? _autoDismiss;

  @override
  void initState() {
    super.initState();
    // A banner could have been armed in the same frame the host mounted.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final PushTapPayload? payload = ref.read(activeBannerProvider);
      if (payload != null && _entry == null) {
        _show(payload);
      }
    });
  }

  @override
  void dispose() {
    _autoDismiss?.cancel();
    _entry?.remove();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<PushTapPayload?>(activeBannerProvider,
        (PushTapPayload? previous, PushTapPayload? next) {
      if (next == null) {
        _hide(clearProvider: false);
      } else if (_entry == null) {
        _show(next);
      }
    });
    return widget.child;
  }

  void _show(PushTapPayload payload) {
    final OverlayState? overlay = AppRoutes.navigatorKey.currentState?.overlay;
    if (overlay == null) {
      return; // No navigator yet — the provider keeps the banner pending.
    }
    final OverlayEntry entry = OverlayEntry(
      builder: (BuildContext context) => _Banner(
        payload: payload,
        onTap: () => _onTap(payload),
      ),
    );
    overlay.insert(entry);
    _entry = entry;
    _autoDismiss?.cancel();
    _autoDismiss = Timer(foregroundBannerDuration, () {
      // The recorded rule: an untouched banner steps aside on its own —
      // dismissal never navigates (the alert stays in history).
      _hide(clearProvider: true);
    });
  }

  void _onTap(PushTapPayload payload) {
    _hide(clearProvider: true);
    // Banner tap = notification tap (MT-5.9-02 AC): same routing seam,
    // same unlock precedence, same destination.
    ref.read(pendingNotificationTapProvider.notifier).arm(payload);
  }

  void _hide({required bool clearProvider}) {
    _autoDismiss?.cancel();
    _autoDismiss = null;
    _entry?.remove();
    _entry = null;
    if (clearProvider && ref.read(activeBannerProvider) != null) {
      ref.read(activeBannerProvider.notifier).state = null;
    }
  }
}

/// The banner strip: payload content only (short title + canonical event
/// type — nothing fetched, nothing enriched, Section 14.2 / MT-5.4-02).
class _Banner extends StatelessWidget {
  const _Banner({required this.payload, required this.onTap});

  final PushTapPayload payload;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final String title =
        payload.title.isEmpty ? payload.eventType : payload.title;
    final String? subtitle = payload.title.isEmpty ? null : payload.eventType;
    return Align(
      alignment: Alignment.topCenter,
      child: SafeArea(
        bottom: false,
        child: Material(
          color: theme.colorScheme.inversePrimary,
          elevation: 6,
          child: InkWell(
            key: const ValueKey<String>('foreground-banner-tap'),
            onTap: onTap,
            child: Padding(
              key: const ValueKey<String>('foreground-banner'),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: <Widget>[
                  Icon(Icons.notifications, color: theme.colorScheme.primary),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Text(
                          title,
                          key:
                              const ValueKey<String>('foreground-banner-title'),
                          style: theme.textTheme.bodyMedium
                              ?.copyWith(fontWeight: FontWeight.w600),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (subtitle != null)
                          Text(
                            subtitle,
                            key: const ValueKey<String>(
                              'foreground-banner-event-type',
                            ),
                            style: theme.textTheme.bodySmall
                                ?.copyWith(color: theme.colorScheme.outline),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
