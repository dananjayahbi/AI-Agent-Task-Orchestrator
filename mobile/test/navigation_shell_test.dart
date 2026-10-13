import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/app.dart';
import 'package:orchestrator_mobile/app/nav_shell.dart';
import 'package:orchestrator_mobile/app/routes.dart';
import 'package:orchestrator_mobile/core/offline/json_cache.dart';
import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/board/board_repository.dart';
import 'package:orchestrator_mobile/features/board/projects_repository.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_summary.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_summary_source.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart'
    hide DashboardSummary, ProjectDashboardCard;

import 'board/board_test_support.dart';
import 'dashboard/dashboard_test_support.dart';
import 'realtime/realtime_test_support.dart';
import 'security/security_test_support.dart';

/// Navigation shell integrity (MT-5.5-01, kept honest through WP-5.6):
/// every Section 14.1 area is reachable — the four tab areas through the
/// shell (Home and Board now render their real WP-5.6 screens), the flow
/// and modal areas through their routes. Remaining placeholders must be
/// honest empty states.
void main() {
  Future<void> pumpApp(WidgetTester tester) async {
    // No stored credential → the MT-5.5-04 gate passes the shell through
    // (onboarding runs inside the app), so the shell is what these
    // navigation checks exercise. Feature seams are faked: no real HTTP,
    // no real preferences, no real stream.
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          secureTokenStoreProvider
              .overrideWithValue(InMemorySecureTokenStore()),
          biometricAuthProvider.overrideWithValue(FakeBiometricAuthenticator()),
          jsonCacheProvider.overrideWithValue(InMemoryJsonCache()),
          dashboardSummarySourceProvider.overrideWithValue(
            FakeDashboardSummarySource()
              ..next = summaryOf(<ProjectDashboardCard>[
                dashboardCard(
                  projectId: 'PID00001',
                  name: 'Nav project',
                  counts: <StateEnum, int>{StateEnum.draft: 1},
                ),
              ]),
          ),
          projectsRepositoryProvider
              .overrideWithValue(FakeProjectsRepository()),
          boardRepositoryProvider.overrideWithValue(FakeBoardRepository()),
          sseClientProvider.overrideWithValue(
            buildTestSseClient(transport: FakeSseTransport()),
          ),
        ],
        child: const OrchestratorApp(),
      ),
    );
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
      // Home is the default tab and now renders the real WP-5.6
      // dashboard (MT-5.6-01), not a placeholder.
      expect(find.text('Home / Overview'), findsOneWidget);
      expect(find.text('Nav project'), findsOneWidget);
      expect(find.textContaining('Not implemented yet'), findsNothing);
    });

    testWidgets('every tab area is reachable by tapping its destination',
        (tester) async {
      await pumpApp(tester);

      // NavigationBar label -> a fragment unique to that area's content.
      // The last flag says whether the area is still a placeholder.
      const List<(String, String, bool)> tabs = <(String, String, bool)>[
        ('Board', 'Select a project above to see its board.', false),
        ('Notifications', 'per-event-type toggles', true),
        ('Settings', 'Device info', true),
        ('Home', 'Nav project', false),
      ];
      for (final (String navLabel, String fragment, bool placeholder) in tabs) {
        await tester.tap(find.text(navLabel));
        await tester.pumpAndSettle();
        expect(
          find.textContaining(fragment),
          findsOneWidget,
          reason: 'tab "$navLabel" must render its content',
        );
        expect(
          find.textContaining('Not implemented yet'),
          placeholder ? findsOneWidget : findsNothing,
          reason: placeholder
              ? 'tab "$navLabel" must still render its honest placeholder'
              : 'tab "$navLabel" must render the real WP-5.6 screen',
        );
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

      // Onboarding is fully implemented (MT-5.5-06), so it is excluded
      // from the placeholder list and checked below.
      const List<AppArea> pushedAreas = <AppArea>[
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

    testWidgets(
        'the onboarding route renders the real flow, not a '
        'placeholder', (tester) async {
      await pumpApp(tester);
      final NavigatorState navigator =
          tester.state<NavigatorState>(find.byType(Navigator));

      navigator.pushNamed(AppArea.onboarding.path);
      await tester.pumpAndSettle();

      expect(find.text('Onboarding'), findsOneWidget);
      expect(find.textContaining('Not implemented yet'), findsNothing);
      // MT-5.5-06: the URL entry step is the flow's first screen.
      expect(find.byKey(const ValueKey<String>('onboarding-server-url-field')),
          findsOneWidget);
      navigator.pop();
      await tester.pumpAndSettle();
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
