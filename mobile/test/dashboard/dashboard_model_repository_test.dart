import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/api/api_exception.dart';
import 'package:orchestrator_mobile/core/offline/json_cache.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_providers.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_repository.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_summary.dart';
import 'package:orchestrator_mobile/features/dashboard/dashboard_summary_source.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import 'dashboard_test_support.dart';

/// MT-5.6-01 unit battery: summary parsing against the documented wire
/// shape, the Section 14.2 read-only cache round-trip, and the separate
/// loading / ready / error / offline-stale screen states.
void main() {
  group('DashboardSummary parsing (Section 9.2 shape, tolerant reader)', () {
    test('parses cards with canonical state keys, velocity, active agents', () {
      final DashboardSummary? parsed = DashboardSummary.tryParse(
        <String, dynamic>{
          'projects': <Object?>[
            <String, dynamic>{
              'project_id': 'PID00001',
              'name': 'Orchestrator',
              'state_counts': <String, int>{
                'draft': 2,
                'pending': 1,
                'in_progress': 3,
                'to_be_audited': 0,
                'in_human_review': 1,
                'completed': 7,
                'not_a_state': 99, // unknown key ignored
              },
              'velocity': 12,
              'active_agents': 3,
            },
          ],
        },
      );

      expect(parsed, isNotNull);
      final ProjectDashboardCard card = parsed!.projects.single;
      expect(card.projectId, 'PID00001');
      expect(card.velocity, 12);
      expect(card.activeAgents, 3);
      // Canonical enum keys, not hand-copied strings (G-01).
      expect(card.stateCounts[StateEnum.inHumanReview], 1);
      expect(card.stateCounts.length, 6,
          reason: 'unknown wire keys must not become states');
      expect(parsed.needsReviewCount, 1);
    });

    test('wrong top-level shape is null (honest error, not empty data)', () {
      expect(DashboardSummary.tryParse(<String, dynamic>{'items': 1}), isNull);
      expect(
        DashboardSummary.tryParse(<String, dynamic>{'projects': 'nope'}),
        isNull,
      );
    });

    test('malformed rows are skipped; absent numerics default to 0', () {
      final DashboardSummary? parsed = DashboardSummary.tryParse(
        <String, dynamic>{
          'projects': <Object?>[
            'not a map',
            <String, dynamic>{'project_id': '', 'name': 'x'},
            <String, dynamic>{'project_id': 'PID2', 'name': 'ok'},
          ],
        },
      );
      expect(parsed!.projects, hasLength(1));
      expect(parsed.projects.single.velocity, 0);
      expect(parsed.projects.single.activeAgents, 0);
      expect(parsed.needsReviewCount, 0);
    });

    test('toWire round-trips through the cache serializer', () {
      final DashboardSummary summary = summaryOf(<ProjectDashboardCard>[
        dashboardCard(
          projectId: 'PID00001',
          name: 'Orchestrator',
          counts: <StateEnum, int>{StateEnum.inHumanReview: 2},
          velocity: 5,
          activeAgents: 1,
        ),
      ]);
      final DashboardSummary? again =
          DashboardSummary.tryParse(summary.toWire());
      expect(again!.projects.single.stateCounts[StateEnum.inHumanReview], 2);
      expect(again.projects.single.velocity, 5);
      expect(jsonEncode(summary.toWire()), contains('in_human_review'),
          reason: 'canonical G-01 wire spelling');
    });
  });

  group('DashboardRepository (Section 14.2 read-only cache)', () {
    test('success caches the summary; failure then serves it stale', () async {
      final FakeDashboardSummarySource source = FakeDashboardSummarySource()
        ..next = summaryOf(<ProjectDashboardCard>[
          dashboardCard(projectId: 'P1', name: 'One'),
        ]);
      final InMemoryJsonCache cache = InMemoryJsonCache();
      final DashboardRepository repository =
          DashboardRepository(source: source, cache: cache);

      final DashboardSnapshot first = await repository.load();
      expect(first.isStale, isFalse);
      expect(first.error, isNull);
      expect(cache.writeCount, 1);
      expect(cache.values[DashboardRepository.cacheKey], contains('P1'));

      source.nextError = catalogError(code: CodeEnum.SERVER_ERROR);
      final DashboardSnapshot second = await repository.load();
      expect(second.isStale, isTrue);
      expect(second.error, isNotNull);
      expect(second.summary.projects.single.projectId, 'P1',
          reason: 'last successful overview is served from cache');
    });

    test('failure with no cache rethrows (honest error state)', () async {
      final FakeDashboardSummarySource source = FakeDashboardSummarySource()
        ..nextError = catalogError(code: CodeEnum.RATE_LIMITED);
      final DashboardRepository repository = DashboardRepository(
        source: source,
        cache: InMemoryJsonCache(),
      );
      await expectLater(
        repository.load(),
        throwsA(
          isA<OrchestratorApiException>().having(
            (OrchestratorApiException e) => e.code,
            'code',
            CodeEnum.RATE_LIMITED,
          ),
        ),
      );
    });

    test('corrupt cache reads as absent, never crashes', () async {
      final FakeDashboardSummarySource source = FakeDashboardSummarySource()
        ..nextError = transportError();
      final InMemoryJsonCache cache = InMemoryJsonCache()
        ..values[DashboardRepository.cacheKey] = '{not json';
      final DashboardRepository repository =
          DashboardRepository(source: source, cache: cache);
      await expectLater(
          repository.load(), throwsA(isA<OrchestratorApiException>()));
    });
  });

  group('DashboardNotifier screen states (Section 20.3)', () {
    late ProviderContainer container;
    late FakeDashboardSummarySource source;
    late InMemoryJsonCache cache;

    ProviderContainer makeContainer() {
      source = FakeDashboardSummarySource();
      cache = InMemoryJsonCache();
      final ProviderContainer c = ProviderContainer(
        overrides: <Override>[
          dashboardSummarySourceProvider.overrideWithValue(source),
          jsonCacheProvider.overrideWithValue(cache),
        ],
      );
      addTearDown(c.dispose);
      return c;
    }

    setUp(() => container = makeContainer());

    test('starts loading, then ready after a successful refresh', () async {
      expect(container.read(dashboardProvider).status, DashboardStatus.loading);
      source.next = summaryOf(<ProjectDashboardCard>[
        dashboardCard(projectId: 'P1', name: 'One'),
      ]);
      await container.read(dashboardProvider.notifier).refresh();
      final DashboardState state = container.read(dashboardProvider);
      expect(state.status, DashboardStatus.ready);
      expect(state.isStale, isFalse);
      expect(state.isEmpty, isFalse);
    });

    test('error with nothing cached is the distinct error state', () async {
      source.nextError = catalogError(code: CodeEnum.SERVER_ERROR);
      await container.read(dashboardProvider.notifier).refresh();
      final DashboardState state = container.read(dashboardProvider);
      expect(state.status, DashboardStatus.error);
      expect(state.error!.code, CodeEnum.SERVER_ERROR);
    });

    test('a later failure keeps the data visible, honestly stale', () async {
      source.next = summaryOf(<ProjectDashboardCard>[
        dashboardCard(projectId: 'P1', name: 'One'),
      ]);
      await container.read(dashboardProvider.notifier).refresh();
      source.nextError = transportError();
      await container.read(dashboardProvider.notifier).refresh();
      final DashboardState state = container.read(dashboardProvider);
      expect(state.status, DashboardStatus.ready);
      expect(state.isStale, isTrue);
      expect(state.summary!.projects.single.name, 'One');
      expect(state.error, isNotNull);
    });

    test('empty summary is a distinct ready-empty state', () async {
      source.next = summaryOf(const <ProjectDashboardCard>[]);
      await container.read(dashboardProvider.notifier).refresh();
      final DashboardState state = container.read(dashboardProvider);
      expect(state.status, DashboardStatus.ready);
      expect(state.isEmpty, isTrue);
    });
  });
}
