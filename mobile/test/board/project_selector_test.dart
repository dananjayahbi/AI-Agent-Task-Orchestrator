import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/features/board/board_screen.dart';
import 'package:orchestrator_mobile/features/board/current_project.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';
import 'board_test_support.dart';

/// MT-5.6-02 widget battery: the Board's project selector over
/// `GET /projects` (via the repository seam → generated client), selection
/// as the single source of truth (board refetch + Section 9.6 stream
/// filter), dashboard preselect, and the distinct empty/error states.
void main() {
  late FakeProjectsRepository projects;
  late FakeBoardRepository board;
  late FakeSseTransport transport;

  setUp(() {
    projects = FakeProjectsRepository();
    board = FakeBoardRepository();
    transport = FakeSseTransport();
  });

  Future<ProviderContainer> pumpBoard(
    WidgetTester tester, {
    String? preselect,
  }) async {
    final Widget app = MaterialApp(home: const BoardScreen());
    await tester.pumpWidget(
      ProviderScope(
        overrides: boardOverrides(
          projects: projects,
          board: board,
          sseClient: buildTestSseClient(transport: transport),
        ),
        child: app,
      ),
    );
    final ProviderContainer container = ProviderScope.containerOf(
      tester.element(find.byType(BoardScreen)),
      listen: false,
    );
    if (preselect != null) {
      container.read(currentProjectProvider.notifier).select(preselect);
      await tester.pump();
    }
    await tester.pumpAndSettle();
    return container;
  }

  testWidgets(
      'selector lists the owner\'s projects (id, name, status) once '
      'loaded; empty and error are distinct (Section 20.3)',
      (WidgetTester tester) async {
    projects.projects = <Project>[
      makeProject(id: 'PID00001', name: 'Orchestrator'),
      makeProject(
        id: 'PID00002',
        name: 'Website',
        activeStatus: ActiveStatusEnum.paused,
      ),
    ];
    await pumpBoard(tester);

    await tester.tap(find.byKey(const ValueKey<String>('project-selector')));
    await tester.pumpAndSettle();
    expect(find.text('Orchestrator (PID00001, active)'), findsOneWidget);
    expect(find.text('Website (PID00002, paused)'), findsOneWidget);
  });

  testWidgets(
      'changing selection refetches the board for the new project and '
      're-filters the SSE subscription (Section 9.6) — one source of truth',
      (WidgetTester tester) async {
    projects.projects = <Project>[
      makeProject(id: 'PID00001', name: 'One'),
      makeProject(id: 'PID00002', name: 'Two'),
    ];
    board.tasksByProject['PID00002'] = <Task>[
      makeTask(
        id: 'PID00002-T1',
        projectId: 'PID00002',
        state: StateEnum.draft,
        title: 'Two task',
      ),
    ];
    final ProviderContainer container = await pumpBoard(tester);

    expect(container.read(currentProjectProvider), isNull);
    expect(board.taskListCalls, isEmpty,
        reason: 'no project selected → nothing to fetch');

    await tester.tap(find.byKey(const ValueKey<String>('project-selector')));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey<String>('project-option-PID00002')),
    );
    await tester.pumpAndSettle();

    expect(container.read(currentProjectProvider), 'PID00002');
    expect(board.listCallsFor('PID00002'), 1,
        reason: 'board refetched for the new selection');
    expect(container.read(sseClientProvider).projectFilter, 'PID00002',
        reason: 'stream filter follows the same provider (single truth)');
    expect(find.byKey(const ValueKey<String>('board-card-PID00002-T1')),
        findsOneWidget);
  });

  testWidgets(
      'a dashboard preselect lands on the Board with that project already '
      'selected and its board loaded (MT-5.6-01 → MT-5.6-02)',
      (WidgetTester tester) async {
    projects.projects = <Project>[
      makeProject(id: 'PID00001', name: 'One'),
      makeProject(id: 'PID00002', name: 'Two'),
    ];
    board.tasksByProject['PID00001'] = <Task>[
      makeTask(
        id: 'PID00001-T1',
        projectId: 'PID00001',
        state: StateEnum.draft,
        title: 'Preselected',
      ),
    ];
    await pumpBoard(tester, preselect: 'PID00001');

    expect(board.listCallsFor('PID00001'), 1);
    expect(
      find.byKey(const ValueKey<String>('board-card-PID00001-T1')),
      findsOneWidget,
    );
    // The selector shows the preselected project (Form state synced).
    expect(
      find.descendant(
        of: find.byKey(const ValueKey<String>('project-selector')),
        matching: find.textContaining('PID00001'),
      ),
      findsOneWidget,
    );
  });

  testWidgets(
      'single project: auto-selected while the selector stays visible '
      '(recorded MT-5.6-02 decision); board loads it',
      (WidgetTester tester) async {
    projects.projects = <Project>[
      makeProject(id: 'PID00001', name: 'Solo'),
    ];
    board.tasksByProject['PID00001'] = <Task>[
      makeTask(id: 'PID00001-T1', projectId: 'PID00001'),
    ];
    final ProviderContainer container = await pumpBoard(tester);

    expect(container.read(currentProjectProvider), 'PID00001');
    expect(
        find.byKey(const ValueKey<String>('project-selector')), findsOneWidget,
        reason: 'selector stays visible with one project');
    expect(board.listCallsFor('PID00001'), 1);
  });

  testWidgets('no projects: empty guidance, board asks for a selection',
      (WidgetTester tester) async {
    projects.projects = <Project>[];
    final ProviderContainer container = await pumpBoard(tester);

    expect(find.byKey(const ValueKey<String>('project-selector-empty')),
        findsOneWidget);
    expect(find.textContaining('No projects yet'), findsOneWidget);
    expect(container.read(currentProjectProvider), isNull);
    expect(
        find.byKey(const ValueKey<String>('board-no-project')), findsOneWidget);
  });

  testWidgets(
      'projects error is distinct, catalog-mapped, and retry recovers '
      '(Section 20.4 item 5)', (WidgetTester tester) async {
    projects.nextError = catalogError(code: CodeEnum.SERVER_ERROR);
    await pumpBoard(tester);

    expect(find.byKey(const ValueKey<String>('project-selector-error')),
        findsOneWidget);
    expect(
      find.text('The server had a problem — try again in a moment.'),
      findsOneWidget,
    );
    expect(find.textContaining('raw server detail'), findsNothing);

    projects.projects = <Project>[makeProject(id: 'PID00001', name: 'Back')];
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(
        find.byKey(const ValueKey<String>('project-selector')), findsOneWidget);
    expect(projects.fetchCount, 2);
  });
}
