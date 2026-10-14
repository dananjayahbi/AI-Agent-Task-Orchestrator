import 'package:flutter/material.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../features/audit_log/audit_log_screen.dart';
import '../features/board/board_screen.dart';
import '../features/home/home_screen.dart';
import '../features/notifications/notifications_screen.dart';
import '../features/onboarding/onboarding_screen.dart';
import '../features/review/review_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/task_detail/attachment_viewer_screen.dart';
import '../features/task_detail/task_detail_screen.dart';
import 'nav_shell.dart';

/// The eight screen areas of parent plan Section 14.1, each with its route.
///
/// This enum is the single source of truth for area names and paths: the
/// navigation shell, the route table and the widget tests all derive from it.
enum AppArea {
  onboarding('Onboarding', '/onboarding'),
  home('Home / Overview', '/home'),
  board('Board', '/board'),
  taskDetail('Task detail', '/task-detail'),
  review('Review sheet', '/review'),
  notifications('Notifications', '/notifications'),
  auditLog('Audit log', '/audit-log'),
  settings('Settings', '/settings');

  const AppArea(this.label, this.path);

  /// Human-readable name from parent plan Section 14.1.
  final String label;

  /// Named route that renders this area.
  final String path;
}

/// Route names used across the app.
abstract final class AppRoutes {
  /// Navigation shell hosting the tab areas (Home, Board, Notifications,
  /// Settings).
  static const String root = '/';

  /// Route for a Section 14.1 area.
  static String forArea(AppArea area) => area.path;

  /// Attachment viewer (MT-5.7-03) — arguments carry the [Attachment]
  /// row (deep-link readiness by id is WP-5.9).
  static const String attachmentViewer = '/attachment-viewer';
}

/// Builds the [MaterialPageRoute] for [settings.name].
///
/// [AppRoutes.root] renders the navigation shell; every Section 14.1 area also
/// has its own route so it can be reached directly (deep links, tests).
/// The task detail route takes the task id as its argument (the board
/// pushes `arguments: task.id`); the attachment viewer takes the
/// attachment row.
Route<dynamic> onGenerateRoute(RouteSettings settings) {
  if (settings.name == AppRoutes.attachmentViewer) {
    final Object? arguments = settings.arguments;
    if (arguments is Attachment) {
      return MaterialPageRoute<dynamic>(
        settings: settings,
        builder: (context) => AttachmentViewerScreen(attachment: arguments),
      );
    }
    return onUnknownRoute(settings);
  }
  final AppArea? area = _areaForPath(settings.name);
  if (settings.name == AppRoutes.root || area != null) {
    return MaterialPageRoute<dynamic>(
      settings: settings,
      builder: (context) => area == null
          ? const NavShell()
          : area == AppArea.taskDetail
              ? TaskDetailScreen(taskId: settings.arguments as String?)
              : screenForArea(area),
    );
  }
  return onUnknownRoute(settings);
}

/// Fallback for routes outside the Section 14.1 table.
Route<dynamic> onUnknownRoute(RouteSettings settings) {
  return MaterialPageRoute<dynamic>(
    settings: settings,
    builder: (context) => Scaffold(
      appBar: AppBar(title: const Text('Not found')),
      body: Center(child: Text('No route for "${settings.name ?? '/'}".')),
    ),
  );
}

AppArea? _areaForPath(String? path) {
  for (final AppArea area in AppArea.values) {
    if (area.path == path) {
      return area;
    }
  }
  return null;
}

/// The screen widget for [area] — the single area-to-screen mapping point,
/// shared by the route table and the navigation shell.
Widget screenForArea(AppArea area) {
  switch (area) {
    case AppArea.onboarding:
      return const OnboardingScreen();
    case AppArea.home:
      return const HomeScreen();
    case AppArea.board:
      return const BoardScreen();
    case AppArea.taskDetail:
      // The route table passes the task id argument directly; the bare
      // area mapping (tests, deep-link stub) renders the honest
      // no-task-selected state.
      return const TaskDetailScreen();
    case AppArea.review:
      return const ReviewScreen();
    case AppArea.notifications:
      return const NotificationsScreen();
    case AppArea.auditLog:
      return const AuditLogScreen();
    case AppArea.settings:
      return const SettingsScreen();
  }
}
