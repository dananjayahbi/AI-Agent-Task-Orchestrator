import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/app.dart';
import 'package:orchestrator_mobile/app/nav_shell.dart';
import 'package:orchestrator_mobile/app/routes.dart';

/// Navigation shell integrity (MT-5.5-01): every Section 14.1 area is
/// reachable — the four tab areas through the shell, the flow and modal
/// areas through their routes. Placeholders must be honest empty states.
void main() {
  Future<void> pumpApp(WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: OrchestratorApp()));
    await tester.pumpAndSettle();
  }

  group('navigation shell', () {
    testWidgets('renders with all four tab destinations', (tester) async {
      await pumpApp(tester);

      expect(find.byType(NavigationBar), findsOneWidget);
      for (final String label in const <String>[
        'Home',
        'Board',
        'Notifications',
        'Settings',
      ]) {
        expect(find.text(label), findsOneWidget);
      }
      // Home is the default tab and shows its honest placeholder.
      expect(find.text('Home / Overview'), findsOneWidget);
      expect(find.textContaining('Not implemented yet'), findsOneWidget);
    });

    testWidgets('every tab area is reachable by tapping its destination',
        (tester) async {
      await pumpApp(tester);

      // NavigationBar label -> a fragment unique to that area's placeholder.
      const List<(String, String)> tabs = <(String, String)>[
        ('Board', 'horizontally paged'),
        ('Notifications', 'per-event-type toggles'),
        ('Settings', 'Device info'),
        ('Home', 'needs-review banner'),
      ];
      for (final (String navLabel, String fragment) in tabs) {
        await tester.tap(find.text(navLabel));
        await tester.pumpAndSettle();
        expect(
          find.textContaining('Not implemented yet'),
          findsOneWidget,
          reason: 'tab "$navLabel" must render its placeholder',
        );
        expect(find.textContaining(fragment), findsOneWidget);
      }
    });

    testWidgets('shell index provider tracks the visible tab', (tester) async {
      await pumpApp(tester);
      final Element scope = tester.element(find.byType(NavShell));
      final ProviderContainer container =
          ProviderScope.containerOf(scope, listen: false);
      expect(container.read(shellIndexProvider), 0);

      await tester.tap(find.text('Board'));
      await tester.pumpAndSettle();
      expect(container.read(shellIndexProvider), 1);
    });
  });

  group('Section 14.1 routes', () {
    testWidgets('each pushed area renders its placeholder', (tester) async {
      await pumpApp(tester);
      final NavigatorState navigator =
          tester.state<NavigatorState>(find.byType(Navigator));

      const List<AppArea> pushedAreas = <AppArea>[
        AppArea.onboarding,
        AppArea.taskDetail,
        AppArea.review,
        AppArea.auditLog,
      ];
      for (final AppArea area in pushedAreas) {
        navigator.pushNamed(area.path);
        await tester.pumpAndSettle();
        expect(find.text(area.label), findsOneWidget);
        expect(find.textContaining('Not implemented yet'), findsOneWidget);
        navigator.pop();
        await tester.pumpAndSettle();
      }
    });

    testWidgets('all eight Section 14.1 areas render from the route table',
        (tester) async {
      await pumpApp(tester);
      expect(AppArea.values, hasLength(8));

      final NavigatorState navigator =
          tester.state<NavigatorState>(find.byType(Navigator));
      for (final AppArea area in AppArea.values) {
        navigator.pushNamed(area.path);
        await tester.pumpAndSettle();
        expect(
          find.text(area.label),
          findsOneWidget,
          reason: 'area ${area.name} must render at ${area.path}',
        );
        navigator.pop();
        await tester.pumpAndSettle();
      }
    });
  });
}
