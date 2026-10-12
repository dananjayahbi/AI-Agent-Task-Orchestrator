import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'core/config/app_config.dart';
import 'core/realtime/last_event_id_store.dart';
import 'core/security/auth_gate.dart';
import 'features/onboarding/onboarding_progress_store.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Startup validation (MT-5.5-02): resolve the build-time configuration before
  // any widget is built. A missing or invalid value throws [ConfigException]
  // naming the offending define — fail fast with a clear message instead of
  // rendering an app pointed at the wrong (or no) backend.
  final config = AppConfig.resolveFromEnvironment();

  // The SSE resume marker store (MT-5.5-05) — plain preferences, the id is
  // not a secret (Section 9.6); the device token never goes near it.
  final lastEventIdStore = await SharedPreferencesLastEventIdStore.open();

  // Onboarding progress (MT-5.5-06): a URL confirmed during onboarding
  // overrides the flavor default for every consumer (app_config precedence
  // decision), and an unfinished flow resumes — the app opens on onboarding
  // instead of the shell until the device is registered.
  final progressStore = await SharedPreferencesOnboardingProgressStore.open();
  final String? confirmedUrl = await progressStore.readServerUrl();
  final bool onboardingCompleted = await progressStore.readCompleted();
  final AppConfig effectiveConfig = _validConfirmedUrl(confirmedUrl)
      ? AppConfig(
          flavor: config.flavor,
          apiBaseUrl: confirmedUrl!,
          tunnelHostname: config.tunnelHostname,
        )
      : config;

  runApp(
    ProviderScope(
      overrides: [
        appConfigProvider.overrideWithValue(effectiveConfig),
        lastEventIdStoreProvider.overrideWithValue(lastEventIdStore),
        onboardingProgressStoreProvider.overrideWithValue(progressStore),
        // Unfinished onboarding (fresh install or mid-flow resume) claims
        // screen time; a completed flow leaves the gate in control.
        if (!onboardingCompleted)
          onboardingRequiredProvider.overrideWith((ref) => true),
      ],
      child: const OrchestratorApp(),
    ),
  );
}

/// The persisted onboarding URL was validated when it was written; re-check
/// cheaply at startup so a corrupted preference cannot point the app at a
/// malformed base URL (fall back to the flavor default instead).
bool _validConfirmedUrl(String? url) {
  if (url == null || url.isEmpty) {
    return false;
  }
  final Uri? uri = Uri.tryParse(url);
  return uri != null &&
      (uri.isScheme('http') || uri.isScheme('https')) &&
      uri.host.isNotEmpty;
}
