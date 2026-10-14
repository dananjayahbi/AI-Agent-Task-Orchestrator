import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:orchestrator_mobile/core/api/api_exception.dart';
import 'package:orchestrator_mobile/core/offline/json_cache.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/features/board/board_cache.dart';
import 'package:orchestrator_mobile/features/task_detail/task_detail_repository.dart';
import 'package:orchestrator_mobile/features/task_detail/task_detail_screen.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart'
    hide DashboardSummary, ProjectDashboardCard;

import '../board/board_test_support.dart';
import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';
import 'task_detail_test_support.dart';

/// MT-5.7-01 battery: the Task detail screen — all four Section 14.1
/// areas (summary, criteria, checkpoint region, resolutions,
/// attachments), generated-client wiring, the Section 14.2 offline
/// cached view, catalog-only error states, inert markdown (P10) and the
/// board navigation round trip.
void main() {
  late FakeTaskDetailRepository repository;
  late FakeSseTransport transport;
  late SseClient client;

  Task fixtureTask({String description = '# Do the thing\n\nSome details.'}) =>
      makeTask(
        id: 'PID00001-T1',
        state: StateEnum.inProgress,
        title: 'Fixture task',
      ).rebuild((TaskBuilder b) => b
        ..description = description
        ..acceptanceCriteria.replace(const <String>[
          'It works',
          'Tests are green',
        ])
        ..latestFeedback = 'Mind the scope.');

  setUp(() {
    repository = FakeTaskDetailRepository();
    transport = FakeSseTransport();
    client = buildDetailTestSseClient(transport: transport);
  });

  Future<ProviderContainer> pumpDetail(
    WidgetTester tester, {
    String? taskId = 'PID00001-T1',
    JsonCache? cache,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: taskDetailOverrides(
          repository: repository,
          cache: cache,
          sseClient: client,
        ),
        child: MaterialApp(
          home: Builder(
            builder: (BuildContext context) => Scaffold(
              body: Center(
                child: ElevatedButton(
                  key: const ValueKey<String>('open-detail'),
                  onPressed: () => Navigator.pushNamed(
                    context,
                    '/task-detail',
                    arguments: taskId,
                  ),
                  child: const Text('Open'),
                ),
              ),
            ),
          ),
          routes: <String, WidgetBuilder>{
            '/task-detail': (BuildContext context) => TaskDetailScreen(
                  taskId: ModalRoute.of(context)!.settings.arguments as String?,
                ),
          },
        ),
      ),
    );
    return ProviderScope.containerOf(
      tester.element(find.byType(ElevatedButton)),
      listen: false,
    );
  }

  /// Pumps the screen directly (no navigation) for content assertions.
  /// The viewport is tall because the detail ListView builds its
  /// children lazily — the assertions cover regions below the fold.
  Future<void> pumpDirect(
    WidgetTester tester, {
    String? taskId = 'PID00001-T1',
    JsonCache? cache,
  }) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        overrides: taskDetailOverrides(
          repository: repository,
          cache: cache,
          sseClient: client,
        ),
        child: MaterialApp(
          home: TaskDetailScreen(taskId: taskId),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  group('Section 14.1 areas (MT-5.7-01 acceptance)', () {
    testWidgets(
        'renders summary, criteria, checkpoint region, '
        'resolutions and attachments from the generated client',
        (WidgetTester tester) async {
      repository
        ..tasks['PID00001-T1'] = fixtureTask()
        ..resolutions['PID00001-T1'] = <Resolution>[
          makeResolution(id: 'R1'),
        ]
        ..attachments['PID00001-T1'] = <Attachment>[
          makeAttachment(id: 'A1'),
        ]
        ..checkpointPages['PID00001-T1'] = <CheckpointPage>[
          CheckpointPage(checkpoints: <Checkpoint>[
            makeCheckpoint(id: 'C1', message: 'Halfway'),
          ]),
        ];
      await pumpDirect(tester);

      // Summary.
      expect(find.byKey(const ValueKey<String>('task-detail-title')),
          findsOneWidget);
      expect(find.text('Fixture task'), findsOneWidget);
      expect(
        find.byKey(const ValueKey<String>('task-detail-state')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey<String>('task-detail-priority')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey<String>('task-detail-description')),
        findsOneWidget,
      );
      // Latest feedback renders when set (Section 7.2).
      expect(find.text('Mind the scope.'), findsOneWidget);

      // Criteria.
      expect(find.byKey(const ValueKey<String>('task-detail-criterion-0')),
          findsOneWidget);
      expect(find.text('It works'), findsOneWidget);
      expect(find.text('Tests are green'), findsOneWidget);

      // Checkpoint stream region (live content is MT-5.7-02's).
      expect(find.byKey(const ValueKey<String>('checkpoint-feed-list')),
          findsOneWidget);
      expect(find.text('Halfway'), findsOneWidget);

      // Resolutions (summaries only).
      expect(
        find.byKey(const ValueKey<String>('task-detail-resolution-R1')),
        findsOneWidget,
      );
      expect(find.textContaining('Attempt 1'), findsOneWidget);

      // Attachments entry points.
      expect(
        find.byKey(const ValueKey<String>('attachment-tile-A1')),
        findsOneWidget,
      );
    });

    testWidgets(
        'empty criteria, resolutions and attachments are honest '
        'empty states, not spinners', (WidgetTester tester) async {
      repository.tasks['PID00001-T1'] = makeTask(id: 'PID00001-T1').rebuild(
        (TaskBuilder b) => b..acceptanceCriteria.clear(),
      );
      await pumpDirect(tester);

      expect(
        find.byKey(const ValueKey<String>('task-detail-no-criteria')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey<String>('task-detail-no-resolutions')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey<String>('attachment-list-empty')),
        findsOneWidget,
      );
      expect(find.text('No attachments.'), findsOneWidget);
    });
  });

  group('states (Section 20.3)', () {
    testWidgets('loading state shows while the fetch is parked',
        (WidgetTester tester) async {
      repository
        ..tasks['PID00001-T1'] = fixtureTask()
        ..held = Completer<void>();
      // Manual pumps: an indeterminate spinner never settles.
      await tester.pumpWidget(
        ProviderScope(
          overrides: taskDetailOverrides(
            repository: repository,
            sseClient: client,
          ),
          child:
              const MaterialApp(home: TaskDetailScreen(taskId: 'PID00001-T1')),
        ),
      );
      await tester.pump();
      await tester.pump();

      expect(
        find.byKey(const ValueKey<String>('task-detail-loading')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey<String>('task-detail-error')),
        findsNothing,
      );
    });

    testWidgets(
        'error state maps catalog codes to friendly copy with a '
        'working retry (Section 20.4 item 5)', (WidgetTester tester) async {
      repository
        ..tasks['PID00001-T1'] = fixtureTask()
        ..nextTaskError = apiError(CodeEnum.TASK_NOT_FOUND, statusCode: 404);
      await pumpDirect(tester);

      expect(
        find.byKey(const ValueKey<String>('task-detail-error')),
        findsOneWidget,
      );
      // The raw server message ("scripted") never reaches the UI.
      expect(find.text('scripted'), findsNothing);

      // Retry succeeds on the second attempt.
      await tester.tap(find.byKey(const ValueKey<String>('task-detail-retry')));
      await tester.pumpAndSettle();
      expect(find.text('Fixture task'), findsOneWidget);
    });

    testWidgets(
        'offline: a failed load falls back to the cached board '
        'row with an honest stale banner (Section 14.2)',
        (WidgetTester tester) async {
      final InMemoryJsonCache cache = InMemoryJsonCache();
      final Task cachedTask = fixtureTask();
      await BoardCache(cache).write('PID00001', <Task>[cachedTask]);

      repository.nextTaskError = OrchestratorApiException.unparsed(
        message: 'no network',
        retryable: true,
      );
      await pumpDirect(tester, cache: cache);

      expect(
        find.byKey(const ValueKey<String>('task-detail-stale-banner')),
        findsOneWidget,
      );
      // The cached summary renders — with no fabricated liveness.
      expect(find.text('Fixture task'), findsOneWidget);
      expect(
        find.byKey(const ValueKey<String>('task-detail-no-resolutions')),
        findsOneWidget,
        reason: 'resolutions are live-only in v1 (recorded decision)',
      );
    });

    testWidgets(
        'a route without a task id renders the honest no-task '
        'state (deep-link readiness, WP-5.9 owns routing)',
        (WidgetTester tester) async {
      await pumpDirect(tester, taskId: null);
      expect(
        find.byKey(const ValueKey<String>('task-detail-no-task')),
        findsOneWidget,
      );
    });
  });

  group('P10 inert markdown', () {
    testWidgets(
        'description markdown renders as data — no script or link '
        'handlers', (WidgetTester tester) async {
      repository.tasks['PID00001-T1'] = fixtureTask(
        description: '# Title\n\nSome *styled* text with a '
            '[link](https://example.com)\n\n<script>alert(1)</script>',
      );
      await pumpDirect(tester);

      // The markdown renders as widgets (heading + text are visible).
      expect(find.text('Title'), findsOneWidget);
      // The script tag is displayed inertly as text, never executed.
      expect(find.textContaining('script'), findsWidgets);
      // The link renders as plain text — the URL is never materialized
      // as a tappable element and no handler leaves the app (P10).
      expect(find.textContaining('https://example.com'), findsNothing);
    });
  });

  group('navigation (MT-5.7-01 acceptance)', () {
    testWidgets('board → detail → back round trip preserves the stack',
        (WidgetTester tester) async {
      repository.tasks['PID00001-T1'] = fixtureTask();
      await pumpDetail(tester);

      await tester.tap(find.byKey(const ValueKey<String>('open-detail')));
      await tester.pumpAndSettle();
      expect(find.text('Fixture task'), findsOneWidget);

      // Back navigation returns to the launching screen.
      final NavigatorState navigator =
          tester.state<NavigatorState>(find.byType(Navigator));
      navigator.pop();
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey<String>('open-detail')), findsOneWidget);
    });

    testWidgets(
        'the screen is addressable by task id (the id drives the '
        'provider family)', (WidgetTester tester) async {
      repository.tasks['PID00001-T7'] = makeTask(
        id: 'PID00001-T7',
        title: 'Seventh task',
      );
      await pumpDirect(tester, taskId: 'PID00001-T7');
      expect(find.text('Seventh task'), findsOneWidget);
      expect(repository.taskCalls, 1);
    });
  });

  group('live row refetch (Section 9.6 consumption)', () {
    testWidgets('a task.updated event triggers one targeted row refetch',
        (WidgetTester tester) async {
      repository.tasks['PID00001-T1'] = fixtureTask();
      // First load; then the event-driven refetch returns an updated row.
      await pumpDirect(tester);
      expect(repository.taskCalls, 1);

      repository.updatedTasks['PID00001-T1'] = fixtureTask().rebuild(
        (TaskBuilder b) => b
          ..title = 'Renamed task'
          ..version = 2,
      );
      transport.queueStream();
      await client.start();
      transport.emitTo(
        0,
        envelopeJson(
          id: 1,
          type: 'task.updated',
          taskId: 'PID00001-T1',
          data: <String, dynamic>{'task_version': 2},
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Renamed task'), findsOneWidget,
          reason: 'the row refetch replaces the summary');
      expect(repository.taskCalls, 2,
          reason: 'exactly one targeted refetch, no resolutions reload');

      await client.dispose();
    });

    testWidgets('events for other tasks or unknown types are ignored',
        (WidgetTester tester) async {
      repository.tasks['PID00001-T1'] = fixtureTask();
      await pumpDirect(tester);
      expect(repository.taskCalls, 1);

      transport.queueStream();
      await client.start();
      transport.emitTo(
        0,
        envelopeJson(
          id: 1,
          type: 'task.updated',
          taskId: 'PID00001-T99',
          data: <String, dynamic>{},
        ),
      );
      transport.emitTo(
        0,
        envelopeJson(
          id: 2,
          type: 'system.alert',
          taskId: 'PID00001-T1',
          data: <String, dynamic>{},
        ),
      );
      await tester.pumpAndSettle();
      expect(repository.taskCalls, 1,
          reason: 'no refetch for other tasks or non-catalog types');

      await client.dispose();
    });
  });
}
