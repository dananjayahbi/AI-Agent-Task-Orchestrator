import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/config/app_config.dart';

/// Environment flavor resolution (MT-5.5-02): per-flavor URLs come from
/// build configuration, prod fails fast without one, and the resolved config
/// is the single source of the base URL.
void main() {
  Map<String, Object?> readDefineFile(String path) {
    final File file = File(path);
    expect(file.existsSync(), isTrue, reason: '$path must be committed');
    return jsonDecode(file.readAsStringSync()) as Map<String, Object?>;
  }

  group('committed define files (env/)', () {
    test('dev.json carries the documented LAN development default', () {
      final Map<String, Object?> defines = readDefineFile('env/dev.json');
      expect(defines['ORCHESTRATOR_FLAVOR'], 'dev');
      final String url = defines['ORCHESTRATOR_API_BASE_URL']! as String;
      final Uri uri = Uri.parse(url);
      expect(uri.isScheme('http'), isTrue);
      expect(uri.port, 8000, reason: 'ORCHESTRATOR_PORT_BACKEND default');
      expect(uri.path, '/api/v1');
    });

    test('prod.json commits no environment-specific URL or hostname', () {
      final Map<String, Object?> defines = readDefineFile('env/prod.json');
      expect(defines['ORCHESTRATOR_FLAVOR'], 'prod');
      expect(defines.containsKey('ORCHESTRATOR_API_BASE_URL'), isFalse,
          reason: 'prod URL is a build-time input (Section 20.4 item 3)');
      expect(defines.containsKey('ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME'),
          isFalse,
          reason: 'no personal tunnel hostname in Git (Section 20.4 item 3)');
    });
  });

  group('AppConfig.resolve', () {
    test('dev flavor resolves the supplied base URL', () {
      final AppConfig config = AppConfig.resolve(
        flavor: 'dev',
        baseUrl: 'http://10.0.2.2:8000/api/v1',
      );
      expect(config.flavor, AppFlavor.dev);
      expect(config.apiBaseUrl, 'http://10.0.2.2:8000/api/v1');
      expect(config.apiOrigin.toString(), 'http://10.0.2.2:8000');
    });

    test('prod flavor with missing URL fails fast naming the define', () {
      expect(
        () => AppConfig.resolve(flavor: 'prod', baseUrl: ''),
        throwsA(
          isA<ConfigException>().having(
            (ConfigException e) => e.message,
            'message',
            allOf(
              contains('ORCHESTRATOR_API_BASE_URL'),
              contains('prod'),
            ),
          ),
        ),
      );
    });

    test('prod flavor derives the URL from the tunnel hostname', () {
      final AppConfig config = AppConfig.resolve(
        flavor: 'prod',
        baseUrl: '',
        tunnelHostname: 'orchestrator.example.com',
      );
      expect(config.apiBaseUrl, 'https://orchestrator.example.com/api/v1');
      expect(config.tunnelHostname, 'orchestrator.example.com');
    });

    test('tunnel hostname with scheme or path is rejected naming the define',
        () {
      expect(
        () => AppConfig.resolve(
          flavor: 'prod',
          baseUrl: '',
          tunnelHostname: 'https://orchestrator.example.com/',
        ),
        throwsA(
          isA<ConfigException>().having(
            (ConfigException e) => e.message,
            'message',
            contains('ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME'),
          ),
        ),
      );
    });

    test('dev flavor with missing URL fails fast naming the define', () {
      expect(
        () => AppConfig.resolve(flavor: 'dev', baseUrl: ''),
        throwsA(
          isA<ConfigException>().having(
            (ConfigException e) => e.message,
            'message',
            contains('ORCHESTRATOR_API_BASE_URL'),
          ),
        ),
      );
    });

    test('unknown or missing flavor fails fast naming ORCHESTRATOR_FLAVOR', () {
      expect(
        () => AppConfig.resolve(flavor: 'staging', baseUrl: 'http://x/y'),
        throwsA(
          isA<ConfigException>().having(
            (ConfigException e) => e.message,
            'message',
            contains('ORCHESTRATOR_FLAVOR'),
          ),
        ),
      );
      expect(
        () => AppConfig.resolve(flavor: '', baseUrl: 'http://x/y'),
        throwsA(isA<ConfigException>()),
      );
    });

    test('non-absolute base URL is rejected', () {
      expect(
        () => AppConfig.resolve(flavor: 'dev', baseUrl: 'not-a-url'),
        throwsA(isA<ConfigException>()),
      );
      expect(
        () => AppConfig.resolve(flavor: 'dev', baseUrl: 'ftp://host/api/v1'),
        throwsA(isA<ConfigException>()),
      );
    });

    test('resolveFromEnvironment fails fast when no defines were passed', () {
      // This is what a bare `flutter run` without env/*.json produces:
      // startup aborts before the first frame (Section 9.10/16.2).
      expect(AppConfig.resolveFromEnvironment, throwsA(isA<ConfigException>()));
    });
  });

  group('single source of the base URL', () {
    test('appConfigProvider exposes exactly the resolved config', () {
      final AppConfig config = AppConfig.resolve(
        flavor: 'dev',
        baseUrl: 'http://10.0.2.2:8000/api/v1',
      );
      final ProviderContainer container = ProviderContainer(
        overrides: [appConfigProvider.overrideWithValue(config)],
      );
      addTearDown(container.dispose);
      expect(container.read(appConfigProvider), same(config));
      expect(
        container.read(appConfigProvider).apiOrigin.toString(),
        'http://10.0.2.2:8000',
      );
    });
  });

  group('flavors install side by side (distinct app ids)', () {
    test('Android product flavors with dev applicationId suffix', () {
      final String gradle =
          File('android/app/build.gradle.kts').readAsStringSync();
      expect(gradle, contains('create("dev")'));
      expect(gradle, contains('create("prod")'));
      expect(gradle, contains('applicationIdSuffix = ".dev"'));
      expect(
        File('android/app/src/dev/res/values/strings.xml').readAsStringSync(),
        contains('Orchestrator Dev'),
      );
      expect(
        File('android/app/src/prod/res/values/strings.xml').readAsStringSync(),
        contains('>Orchestrator<'),
      );
    });

    test('iOS flavor schemes, configs and dev bundle suffix exist', () {
      final String pbxproj = File(
        'ios/Runner.xcodeproj/project.pbxproj',
      ).readAsStringSync();
      expect(
        pbxproj,
        contains('com.aiagenttaskorchestrator.orchestratorMobile.dev'),
      );
      for (final String config in const <String>[
        'Debug-Dev',
        'Profile-Dev',
        'Release-Dev',
        'Debug-Prod',
        'Profile-Prod',
        'Release-Prod',
      ]) {
        expect(pbxproj, contains('name = "$config";'),
            reason: 'build configuration $config must exist');
      }
      expect(
        File('ios/Runner.xcodeproj/xcshareddata/xcschemes/Dev.xcscheme')
            .readAsStringSync(),
        contains('buildConfiguration = "Debug-Dev"'),
      );
      expect(
        File('ios/Runner.xcodeproj/xcshareddata/xcschemes/Prod.xcscheme')
            .readAsStringSync(),
        contains('buildConfiguration = "Debug-Prod"'),
      );
      expect(
        File('ios/Runner/Info.plist').readAsStringSync(),
        contains(r'$(APP_DISPLAY_NAME)'),
      );
    });
  });
}
