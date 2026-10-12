import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Persistence for onboarding progress (MT-5.5-06 "resumable"): the step
/// index, the confirmed server URL and the completion marker survive an
/// app restart. None is secret (Section 12.4 covers credentials only) —
/// plain preferences are appropriate, the same documented choice as the
/// SSE resume marker.
///
/// The owner session token and the device token are deliberately **not**
/// persisted here: the session lives in memory for the flow's duration and
/// the device token goes only to platform secure storage via the gate.
abstract class OnboardingProgressStore {
  Future<int?> readStep();
  Future<void> writeStep(int stepIndex);

  Future<String?> readServerUrl();
  Future<void> writeServerUrl(String url);

  /// True once the flow finished (registration + enrollment done or
  /// honestly skipped). Separate from the step index because the last
  /// step and "finished" would otherwise share an index.
  Future<bool> readCompleted();
  Future<void> writeCompleted(bool completed);
}

/// SharedPreferences-backed store (async singleton load).
class SharedPreferencesOnboardingProgressStore
    implements OnboardingProgressStore {
  SharedPreferencesOnboardingProgressStore(this._prefs);

  static const String stepKey = 'onboarding_step';
  static const String serverUrlKey = 'onboarding_server_url';
  static const String completedKey = 'onboarding_completed';

  final SharedPreferences _prefs;

  static Future<SharedPreferencesOnboardingProgressStore> open() async =>
      SharedPreferencesOnboardingProgressStore(
          await SharedPreferences.getInstance());

  @override
  Future<int?> readStep() async => _prefs.getInt(stepKey);

  @override
  Future<void> writeStep(int stepIndex) async =>
      _prefs.setInt(stepKey, stepIndex);

  @override
  Future<String?> readServerUrl() async => _prefs.getString(serverUrlKey);

  @override
  Future<void> writeServerUrl(String url) async =>
      _prefs.setString(serverUrlKey, url);

  @override
  Future<bool> readCompleted() async => _prefs.getBool(completedKey) ?? false;

  @override
  Future<void> writeCompleted(bool completed) async =>
      _prefs.setBool(completedKey, completed);
}

/// The persisted onboarding progress (MT-5.5-06). `main()` opens the
/// concrete store before `runApp`: it seeds [appConfigProvider]'s URL with
/// the onboarding-confirmed server address (overriding the flavor default —
/// app_config precedence decision) and seeds [onboardingRequiredProvider]
/// so a fresh or mid-flow install renders onboarding instead of the shell.
final Provider<OnboardingProgressStore> onboardingProgressStoreProvider =
    Provider<OnboardingProgressStore>(
  (Ref ref) => throw UnimplementedError(
    'Override onboardingProgressStoreProvider with a concrete store '
    '(SharedPreferencesOnboardingProgressStore in app wiring).',
  ),
);
