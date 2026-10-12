import 'package:flutter/material.dart';

import '../core/realtime/sse_lifecycle_binder.dart';
import '../core/security/lock_gate.dart';
import '../core/theme/app_theme.dart';
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
      onGenerateRoute: onGenerateRoute,
      onUnknownRoute: onUnknownRoute,
      builder: (context, child) => LockGate(
        child: SseLifecycleBinder(child: child ?? const SizedBox()),
      ),
    );
  }
}
