import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/app.dart';
import 'package:orchestrator_mobile/app/nav_shell.dart';
import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/core/realtime/sse_connection_status.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/board/board_repository.dart';
import 'package:orchestrator_mobile/features/board/current_project.dart';
import 'package:orchestrator_mobile/features/board/projects_repository.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_repository.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_summary.dart';
import 'package:orchestrator_mobile/features/home/home_screen.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart'
    hide DashboardSummary, ProjectDashboardCard;

import '../board/board_test_support.dart';
import '../realtime/realtime_test_support.dart';
import '../security/security_test_support.dart';
import 'dashboard_test_support.dart';

/// MT-5.6-01 widget battery: Section 14.1 Home / Overview contents
/// (project cards with per-state counts, velocity, active agents; the
/// needs-review banner), the four separate screen states, the catalog-code
/// friendly error copy, the Section 14.2 offline-stale presentation, the
/// dashboard → board handoff (MT-5.6-02 preselect), and the WP-5.5 gate.
void main() {
  late FakeDashboardSummarySource source;
  late InMemoryJsonCache cache;

  setUp(() {
    source = FakeDashboardSummarySource();
    cache = InMemoryJsonCache();
  });

  List<Override> overrides() => <Override>[
        ...dashboardOverrides(source: source, cache: cache),
        sseClientProvider.overrideWithValue(
            buildTestSseClient(transport: FakeSseTransport())),
      ];

  Future<void> pumpHome(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: overrides(),
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
  }

  DashboardSummary twoProjectSummary() => summaryOf(<ProjectDashboardCard>[
        dashboardCard(
          projectId: 'PID00001',
          name: 'Orchestrator',
          counts: <StateEnum, int>{
            StateEnum.draft: 2,
            StateEnum.inProgress: 4,
            StateEnum.inHumanReview: 3,
          },
          velocity: 12,
          activeAgents: 3,
        ),
        dashboardCard(
          projectId: 'PID00002',
          name: 'Website',
          counts: <StateEnum, int>{StateEnum.completed: 9},
          velocity: 1,
          activeAgents: 0,
        ),
      ]);

  testWidgets('loading state is a distinct skeleton before data arrives',
      (WidgetTester tester) async {
    source.pending = Completer<DashboardSummary>();
    await pumpHome(tester);
    await tester.pump();
    expect(find.byKey(const ValueKey<String>('dashboard-skeleton-0')),
        findsOneWidget);
    expect(find.byKey(const ValueKey<String>('needs-review-banner')),
        findsNothing);
  });

  testWidgets(
      'cards render per-state counts, velocity and active agents; '
      'needs-review banner from in_human_review (Section 14.1)',
      (WidgetTester tester) async {
    source.next = twoProjectSummary();
    await pumpHome(tester);
    await tester.pumpAndSettle();

    expect(find.text('Orchestrator'), findsOneWidget);
    expect(find.text('Website'), findsOneWidget);
    expect(
      find.text('Velocity 12 · 3 active agents'),
      findsOneWidget,
    );
    expect(find.text('Draft 2'), findsOneWidget);
    expect(find.text('In progress 4'), findsOneWidget);
    expect(find.text('Completed 9'), findsOneWidget);
    // Section 14.1 needs-review banner: 3 across the cards.
    expect(find.byKey(const ValueKey<String>('needs-review-banner')),
        findsOneWidget);
    expect(find.text('3 tasks need your review'), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('needs-review-chip')),
        findsOneWidget);
  });

  testWidgets('banner is absent when nothing needs review',
      (WidgetTester tester) async {
    source.next = summaryOf(<ProjectDashboardCard>[
      dashboardCard(
        projectId: 'PID00001',
        name: 'Quiet project',
        counts: <StateEnum, int>{StateEnum.completed: 5},
        velocity: 5,
      ),
    ]);
    await pumpHome(tester);
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey<String>('needs-review-banner')),
        findsNothing);
    expect(
        find.byKey(const ValueKey<String>('needs-review-chip')), findsNothing);
  });

  testWidgets('empty state (no projects) is distinct',
      (WidgetTester tester) async {
    source.next = summaryOf(const <ProjectDashboardCard>[]);
    await pumpHome(tester);
    await tester.pumpAndSettle();

    expect(find.text('No projects yet.'), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('dashboard-skeleton-0')),
        findsNothing);
    expect(find.byKey(const ValueKey<String>('needs-review-banner')),
        findsNothing);
  });

  testWidgets(
      'error state shows catalog-code friendly copy, never the raw '
      'server message (Section 20.4 item 5), and retry recovers',
      (WidgetTester tester) async {
    source.nextError = catalogError(code: CodeEnum.SERVER_ERROR);
    await pumpHome(tester);
    await tester.pumpAndSettle();

    expect(
      find.text('The server had a problem — try again in a moment.'),
      findsOneWidget,
    );
    expect(
      find.textContaining('raw server detail'),
      findsNothing,
      reason: 'Section 12.4: raw server text never reaches the screen',
    );

    source.next = twoProjectSummary();
    await tester.tap(find.byKey(const ValueKey<String>('dashboard-retry')));
    await tester.pumpAndSettle();
    expect(find.text('Orchestrator'), findsOneWidget);
  });

  testWidgets(
      'offline: last overview served from cache with a clear stale '
      'indication, never presented as live (Section 14.2)',
      (WidgetTester tester) async {
    cache.values[DashboardRepository.cacheKey] =
        jsonEncode(twoProjectSummary().toWire());
    source.nextError = transportError();
    await pumpHome(tester);
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey<String>('dashboard-stale-banner')),
        findsOneWidget);
    expect(find.textContaining('Showing the last loaded overview'),
        findsOneWidget);
    expect(find.text('Orchestrator'), findsOneWidget,
        reason: 'cached cards are shown');
    expect(source.fetchCount, 1, reason: 'network-first, then cache');
  });

  testWidgets(
      'tapping a project card preselects it and lands on the Board tab '
      '(MT-5.6-01 → MT-5.6-02 handoff)', (WidgetTester tester) async {
    source.next = twoProjectSummary();
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          ...overrides(),
          projectsRepositoryProvider
              .overrideWithValue(FakeProjectsRepository()),
          boardRepositoryProvider.overrideWithValue(FakeBoardRepository()),
        ],
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
    await tester.pumpAndSettle();
    final ProviderContainer container = ProviderScope.containerOf(
      tester.element(find.byType(HomeScreen)),
      listen: false,
    );

    await tester.tap(find.byKey(
      const ValueKey<String>('project-card-PID00002'),
    ));
    await tester.pump();

    expect(container.read(currentProjectProvider), 'PID00002');
    expect(container.read(shellIndexProvider), 1,
        reason: 'the shell lands on the Board tab');
    expect(
      container.read(sseClientProvider).projectFilter,
      'PID00002',
      reason: 'the stream filter follows the selection (Section 9.6)',
    );
  });

  testWidgets(
      'catalog events from the shared stream refresh the dashboard with '
      'one debounced fetch (MT-5.6-04 foreground live updates)',
      (WidgetTester tester) async {
    final FakeSseTransport transport = FakeSseTransport()..queueStream();
    final SseClient client = buildTestSseClient(transport: transport);
    source.next = twoProjectSummary();
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          ...dashboardOverrides(source: source, cache: cache),
          sseClientProvider.overrideWithValue(client),
        ],
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(source.fetchCount, 1, reason: 'the initial load');

    await client.start();
    for (int i = 0;
        i < 20 && client.status.value != SseConnectionStatus.connected;
        i++) {
      await tester.pump(const Duration(milliseconds: 5));
    }
    expect(client.status.value, SseConnectionStatus.connected);

    transport.emitTo(
      0,
      envelopeJson(
        id: 1,
        type: 'task.transitioned',
        projectId: 'PID00001',
        taskId: 'PID00001-T1',
        data: <String, dynamic>{'to_state': 'in_progress'},
      ),
    );
    // The 250 ms debounce elapses on the fake clock → exactly one fetch.
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pumpAndSettle();
    expect(source.fetchCount, 2,
        reason: 'one debounced summary refresh per event burst');
    expect(find.text('Orchestrator'), findsOneWidget);

    // Foreground discipline: once the stream stops, no more refreshes.
    await client.pause();
    await tester.pump();
    final int afterPause = source.fetchCount;
    await tester.pump(const Duration(milliseconds: 400));
    expect(source.fetchCount, afterPause);
  });

  testWidgets(
      'the whole screen sits behind the WP-5.5 biometric gate — locked '
      'means no dashboard fetch at all (Section 14.2)',
      (WidgetTester tester) async {
    final InMemorySecureTokenStore store = InMemorySecureTokenStore();
    await store.write(deviceTokenStorageKey, 'tok'); // pragma: allowlist secret

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          secureTokenStoreProvider.overrideWithValue(store),
          biometricAuthProvider.overrideWithValue(FakeBiometricAuthenticator()),
          ...overrides(),
        ],
        child: const OrchestratorApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Orchestrator is locked'), findsOneWidget);
    expect(find.text('Home / Overview'), findsNothing,
        reason: 'the gate hides the authenticated screen entirely');
    expect(source.fetchCount, 0,
        reason: 'no authenticated data is fetched while locked');
  });
}
