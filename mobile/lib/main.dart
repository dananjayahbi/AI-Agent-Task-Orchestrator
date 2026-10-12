import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'core/config/app_config.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Startup validation (MT-5.5-02): resolve the build-time configuration before
  // any widget is built. A missing or invalid value throws [ConfigException]
  // naming the offending define — fail fast with a clear message instead of
  // rendering an app pointed at the wrong (or no) backend.
  final config = AppConfig.resolveFromEnvironment();

  runApp(
    ProviderScope(
      overrides: [appConfigProvider.overrideWithValue(config)],
      child: const OrchestratorApp(),
    ),
  );
}
