import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/app/app.dart';
import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/core/security/auth_gate.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/audit_log/audit_log_repository.dart'
    show auditLogRepositoryProvider;
import 'package:orchestrator_mobile/features/board/board_repository.dart';
import 'package:orchestrator_mobile/features/board/projects_repository.dart';
import 'package:orchestrator_mobile/features/notifications/notification_history.dart';
import 'package:orchestrator_mobile/features/notifications/notification_preferences.dart';

import '../audit_log/audit_log_test_support.dart' show FakeAuditLogRepository;
import '../board/board_test_support.dart'
    show FakeBoardRepository, FakeProjectsRepository, buildTestSseClient;
import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';
import '../review/review_test_support.dart';
import '../security/security_test_support.dart';

/// MT-5.9-01/02/03 shared harness: the full `OrchestratorApp` behind faked
/// feature seams — no real HTTP, no real preferences, no real stream
/// (the navigation-shell test's documented harness requirements).
class NotificationsTestHarness {
  NotificationsTestHarness({
    SecureTokenStore? store,
    BiometricAuthenticator? auth,
  })  : store = store ?? InMemorySecureTokenStore(),
        auth = auth ?? FakeBiometricAuthenticator() {
    reviewRepo = FakeReviewRepository();
    dashSource = FakeDashboardSummarySource()..next = summaryOf([]);
    historyStore = InMemoryNotificationHistoryStore();
    prefsRepo = FakeNotificationPreferencesRepository();
  }

  final SecureTokenStore store;
  final BiometricAuthenticator auth;
  late final FakeReviewRepository reviewRepo;
  late final FakeDashboardSummarySource dashSource;
  late final InMemoryNotificationHistoryStore historyStore;
  late final FakeNotificationPreferencesRepository prefsRepo;

  List<Override> overrides() => <Override>[
        secureTokenStoreProvider.overrideWithValue(store),
        biometricAuthProvider.overrideWithValue(auth),
        ...reviewOverrides(repository: reviewRepo),
        ...dashboardOverrides(
          source: dashSource,
          cache: InMemoryJsonCache(),
        ),
        notificationHistoryStoreProvider.overrideWithValue(historyStore),
        notificationPreferencesRepositoryProvider.overrideWithValue(prefsRepo),
        projectsRepositoryProvider.overrideWithValue(FakeProjectsRepository()),
        boardRepositoryProvider.overrideWithValue(FakeBoardRepository()),
        auditLogRepositoryProvider.overrideWithValue(FakeAuditLogRepository()),
        sseClientProvider.overrideWithValue(
          buildTestSseClient(transport: FakeSseTransport()),
        ),
      ];

  Future<ProviderContainer> pumpApp(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: overrides(),
        child: const OrchestratorApp(),
      ),
    );
    await tester.pumpAndSettle();
    return ProviderScope.containerOf(
      tester.element(find.byType(OrchestratorApp)),
    );
  }

  Future<void> unlock(WidgetTester tester) async {
    await tester.tap(find.text('Unlock'));
    await tester.pumpAndSettle();
  }

  /// Ends an unlocked test by re-locking the gate and pausing the test SSE
  /// client — the released token's inactivity timer is canceled by `lock()`
  /// and the run loop's backoff timer by `pause()` (the test invariant
  /// dislikes either surviving the test body; the pause is explicit because
  /// `LockGate` swaps the whole subtree out and the lifecycle binder's own
  /// `dispose` does not stop a client it started).
  Future<void> endLocked(
    WidgetTester tester,
    ProviderContainer container,
  ) async {
    container.read(authGateProvider.notifier).lock();
    await container.read(sseClientProvider).pause();
    await tester.pumpAndSettle();
  }
}

/// The MT-5.4-02 five-field data map a platform message carries.
Map<String, String> pushTapData({
  String id = 'PID00001-T001',
  String eventType = 'task.transitioned',
  String projectId = 'PID00001',
  String version = '7',
  String title = 'Review me',
}) =>
    <String, String>{
      'event_type': eventType,
      'project_id': projectId,
      'task_id': id,
      'task_version': version,
      'title': title,
    };

/// In-memory [NotificationHistoryStore] for tests.
class InMemoryNotificationHistoryStore implements NotificationHistoryStore {
  final List<NotificationReceipt> rows = <NotificationReceipt>[];
  int loadCalls = 0;
  int saveCalls = 0;
  bool failLoads = false;
  bool failSaves = false;

  /// When set, the next load parks until released (drives loading states).
  Completer<void>? gate;

  @override
  Future<List<NotificationReceipt>> load() async {
    loadCalls += 1;
    final Completer<void>? held = gate;
    if (held != null) {
      gate = null;
      await held.future;
    }
    if (failLoads) {
      throw StateError('history store unavailable');
    }
    return List<NotificationReceipt>.of(rows);
  }

  @override
  Future<void> save(List<NotificationReceipt> receipts) async {
    saveCalls += 1;
    if (failSaves) {
      throw StateError('history store read-only');
    }
    rows
      ..clear()
      ..addAll(receipts);
  }
}

/// Scripted [NotificationPreferencesRepository] (MT-5.9-03): the current
/// set, recorded updates, scripted failures.
class FakeNotificationPreferencesRepository
    implements NotificationPreferencesRepository {
  FakeNotificationPreferencesRepository({
    List<NotificationPreferenceItem>? items,
  }) : items = items ??
            <NotificationPreferenceItem>[
              const NotificationPreferenceItem(
                eventType: 'in_human_review',
                enabled: true,
              ),
              const NotificationPreferenceItem(
                eventType: 'merge_failure',
                enabled: true,
              ),
              const NotificationPreferenceItem(
                eventType: 'retry_exhaustion',
                enabled: true,
              ),
              const NotificationPreferenceItem(
                eventType: 'completion_digest',
                enabled: false,
              ),
            ];

  List<NotificationPreferenceItem> items;
  final List<(String, bool)> updates = <(String, bool)>[];
  Object? nextFetchError;
  Object? nextUpdateError;

  /// When set, the next update parks until released (save-in-flight states).
  Completer<void>? gate;

  @override
  Future<List<NotificationPreferenceItem>> fetchPreferences() async {
    final Object? error = nextFetchError;
    if (error != null) {
      nextFetchError = null;
      throw error;
    }
    return items;
  }

  @override
  Future<List<NotificationPreferenceItem>> updatePreference({
    required String eventType,
    required bool enabled,
  }) async {
    updates.add((eventType, enabled));
    final Completer<void>? held = gate;
    if (held != null) {
      gate = null;
      await held.future;
    }
    final Object? error = nextUpdateError;
    if (error != null) {
      nextUpdateError = null;
      throw error;
    }
    items = <NotificationPreferenceItem>[
      for (final NotificationPreferenceItem item in items)
        item.eventType == eventType ? item.copyWith(enabled: enabled) : item,
    ];
    return items;
  }
}
