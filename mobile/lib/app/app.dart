import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import 'routes.dart';

/// Root widget of the mobile client (parent plan Section 14.1).
///
/// Navigation is route-based: the shell at [AppRoutes.root] hosts the four
/// tab areas; the remaining Section 14.1 areas are pushed as routes.
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
    );
  }
}
