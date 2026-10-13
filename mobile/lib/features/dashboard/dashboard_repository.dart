import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/offline/json_cache.dart';
import 'dashboard_summary.dart';
import 'dashboard_summary_source.dart';

/// One dashboard load's outcome (MT-5.6-01; Section 14.2 read-only cache).
class DashboardSnapshot {
  const DashboardSnapshot({
    required this.summary,
    required this.isStale,
    this.error,
  });

  final DashboardSummary summary;

  /// True when the summary was served from the Section 14.2 offline cache
  /// because the network fetch failed — the UI must present it as stale,
  /// never as live (MT-5.6-01 risk note).
  final bool isStale;

  /// The fetch failure that caused the cache fallback, when stale.
  final OrchestratorApiException? error;
}

/// Cache-aware dashboard reader (Section 14.2: read-only cache of the last
/// overview; mutating actions are not this layer's concern at all).
class DashboardRepository {
  DashboardRepository({required this.source, required this.cache});

  static const String cacheKey = 'dashboard_summary_cache_v1';

  final DashboardSummarySource source;
  final JsonCache cache;

  /// Fetches the summary; on success the result is cached, on failure the
  /// last successful summary is served flagged stale. With no cache and a
  /// failed fetch the failure surfaces to the caller (honest error state,
  /// Section 20.3).
  Future<DashboardSnapshot> load() async {
    try {
      final DashboardSummary summary = await source.fetchSummary();
      await _writeCache(summary);
      return DashboardSnapshot(summary: summary, isStale: false);
    } on OrchestratorApiException catch (error) {
      final DashboardSummary? cached = await _readCache();
      if (cached != null) {
        return DashboardSnapshot(summary: cached, isStale: true, error: error);
      }
      rethrow;
    }
  }

  Future<DashboardSummary?> _readCache() async {
    try {
      final String? raw = await cache.read(cacheKey);
      if (raw == null) {
        return null;
      }
      final Object? decoded = jsonDecode(raw);
      if (decoded is! Map) {
        return null;
      }
      return DashboardSummary.tryParse(Map<String, dynamic>.from(decoded));
    } catch (_) {
      // Corrupt cache entry: treat as absent, never crash the screen.
      return null;
    }
  }

  Future<void> _writeCache(DashboardSummary summary) async {
    try {
      await cache.write(cacheKey, jsonEncode(summary.toWire()));
    } catch (_) {
      // Cache write failure only costs the next offline read — the live
      // load already succeeded, so warn-and-continue is the right tone.
    }
  }
}

/// The dashboard repository wired from the app seams; tests override it or
/// its dependencies.
final Provider<DashboardRepository> dashboardRepositoryProvider =
    Provider<DashboardRepository>(
  (Ref ref) => DashboardRepository(
    source: ref.watch(dashboardSummarySourceProvider),
    cache: ref.watch(jsonCacheProvider),
  ),
);
