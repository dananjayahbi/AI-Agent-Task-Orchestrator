import 'package:flutter/material.dart';

import '../core/realtime/sse_lifecycle_binder.dart';
import '../core/security/lock_gate.dart';
import '../core/theme/app_theme.dart';
import '../features/notifications/foreground_banner.dart';
import '../features/notifications/notification_tap_binder.dart';
import 'routes.dart';

/// Root widget of the mobile client (parent plan Section 14.1).
///
/// Navigation is route-based: the shell at [AppRoutes.root] hosts the four
/// tab areas; the remaining Section 14.1 areas are pushed as routes.
///
/// The whole navigator sits behind [LockGate] (MT-5.5-04, Section 14.2):
/// while the biometric gate is locked, no route renders authenticated data.
/// [SseLifecycleBinder] (MT-5.5-05) keeps the event stream tied to the
/// foreground + unlocked state (Section 14.2).
class OrchestratorApp extends StatelessWidget {
  const OrchestratorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Orchestrator',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      initialRoute: AppRoutes.root,
      navigatorKey: AppRoutes.navigatorKey,
      onGenerateRoute: onGenerateRoute,
      onUnknownRoute: onUnknownRoute,
      // LockGate outermost (gate precedence over routing — Section 14.2);
      // the notification-tap binder (MT-5.9-01) mounts only inside the
      // unlocked branch, so a pending tap routes *after unlock*, and the
      // foreground banner host (MT-5.9-02) never renders while locked.
      builder: (context, child) => LockGate(
        child: NotificationTapBinder(
          child: ForegroundBannerHost(
            child: SseLifecycleBinder(child: child ?? const SizedBox()),
          ),
        ),
      ),
    );
  }
}
