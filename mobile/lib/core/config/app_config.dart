/// Build-time configuration resolved once at startup (MT-5.5-02).
///
/// Vocabulary follows [docs/plan/conventions/configuration.md] — the same
/// names the backend, web and bridge use (parent plan Sections 9.10, 16.2):
///
/// * `ORCHESTRATOR_FLAVOR` — `dev` or `prod`, supplied by the per-flavor
///   dart-define files under `env/`.
/// * `ORCHESTRATOR_API_BASE_URL` — absolute `http(s)` API base URL including
///   the `/api/v1` prefix (the canonical setting name; never committed for
///   `prod` — build-time input only).
/// * `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` — DNS name without scheme
///   (WP-5.1; no environment-specific hostname is committed — Section 20.4
///   item 3). When set, the prod base URL derives from it.
///
/// Precedence (WP-5.5 decision, recorded in the WP changelog): an
/// onboarding-set URL persisted by MT-5.5-06 overrides this flavor default;
/// this object is the build-time layer only.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when the build-time configuration is missing or invalid.
///
/// Startup fails fast with this error (Section 9.10/16.2) so a misconfigured
/// build never renders an app pointed at the wrong backend.
class ConfigException implements Exception {
  ConfigException(this.message);

  final String message;

  @override
  String toString() => 'ConfigException: $message';
}

/// The two build flavors (parent plan Section 14.3).
enum AppFlavor {
  dev('dev'),
  prod('prod');

  const AppFlavor(this.id);

  final String id;

  /// Parses a flavor id, failing fast on anything else.
  static AppFlavor parse(String raw) {
    for (final AppFlavor flavor in AppFlavor.values) {
      if (flavor.id == raw) {
        return flavor;
      }
    }
    throw ConfigException(
      'ORCHESTRATOR_FLAVOR must be "dev" or "prod" but was "${raw.isEmpty ? '(missing)' : raw}". '
      'Run with --dart-define-from-file=env/dev.json or env/prod.json '
      '(see mobile/README.md).',
    );
  }
}

/// The resolved build-time configuration: the single source of the backend
/// base URL for every consumer (generated API client, onboarding).
class AppConfig {
  const AppConfig({
    required this.flavor,
    required this.apiBaseUrl,
    this.tunnelHostname,
  });

  /// Resolves configuration from the compile-time dart-defines.
  ///
  /// Throws [ConfigException] on a missing or invalid value — called from
  /// `main()` before the first frame so startup fails fast (Section 9.10).
  static AppConfig resolveFromEnvironment() => AppConfig.resolve(
        flavor: const String.fromEnvironment('ORCHESTRATOR_FLAVOR'),
        baseUrl: const String.fromEnvironment('ORCHESTRATOR_API_BASE_URL'),
        tunnelHostname: const String.fromEnvironment(
            'ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME'),
      );

  /// Pure resolution logic (separated for tests).
  ///
  /// * `prod` with no base URL derives `https://<tunnel>/api/v1` from
  ///   [tunnelHostname]; with neither value it fails fast naming
  ///   `ORCHESTRATOR_API_BASE_URL` (Section 16.2/9.10).
  /// * `dev` with no base URL fails fast naming `ORCHESTRATOR_API_BASE_URL`
  ///   and pointing at the committed default `env/dev.json`.
  static AppConfig resolve({
    required String flavor,
    required String baseUrl,
    String? tunnelHostname,
  }) {
    final AppFlavor parsedFlavor = AppFlavor.parse(flavor);
    final String host = tunnelHostname?.trim() ?? '';
    if (host.isNotEmpty && (host.contains('://') || host.contains('/'))) {
      throw ConfigException(
        'ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME must be a bare DNS name '
        'without scheme or path (Section 15.1) but was "$host".',
      );
    }

    String url = baseUrl.trim();
    if (url.isEmpty) {
      if (parsedFlavor == AppFlavor.prod && host.isNotEmpty) {
        url = 'https://$host/api/v1';
      } else if (parsedFlavor == AppFlavor.prod) {
        throw ConfigException(
          'The prod flavor is missing its backend URL: set the '
          'ORCHESTRATOR_API_BASE_URL build-time define (or supply '
          'ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME to derive it) — '
          'see mobile/README.md, "Building the prod flavor".',
        );
      } else {
        throw ConfigException(
          'The dev flavor is missing ORCHESTRATOR_API_BASE_URL — run with '
          '--dart-define-from-file=env/dev.json for the documented LAN '
          'development default (see mobile/README.md).',
        );
      }
    }

    final Uri? uri = Uri.tryParse(url);
    if (uri == null ||
        !(uri.isScheme('http') || uri.isScheme('https')) ||
        uri.host.isEmpty) {
      throw ConfigException(
        'ORCHESTRATOR_API_BASE_URL must be an absolute http(s) URL but was '
        '"$url".',
      );
    }

    return AppConfig(
      flavor: parsedFlavor,
      apiBaseUrl: url,
      tunnelHostname: host.isEmpty ? null : host,
    );
  }

  final AppFlavor flavor;

  /// Canonical API base URL including the `/api/v1` prefix.
  final String apiBaseUrl;

  /// Tunnel hostname (DNS name, no scheme) when one was supplied.
  final String? tunnelHostname;

  /// Origin (`scheme://host[:port]`) — the base URL handed to the generated
  /// API client, whose operation paths already carry the `/api/v1` prefix.
  Uri get apiOrigin {
    final Uri uri = Uri.parse(apiBaseUrl);
    return Uri(
        scheme: uri.scheme,
        host: uri.host,
        port: uri.hasPort ? uri.port : null);
  }
}

/// The single source of the resolved configuration for all consumers
/// (Section 14.3 / MT-5.5-02: one resolved-configuration object).
///
/// `main()` resolves eagerly and overrides this provider, so a missing value
/// fails fast before the first frame; tests override it with explicit
/// values.
final Provider<AppConfig> appConfigProvider = Provider<AppConfig>(
  (ref) => AppConfig.resolveFromEnvironment(),
);
