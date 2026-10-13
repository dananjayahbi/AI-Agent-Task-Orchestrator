import 'dart:convert';

import 'package:built_value/serializer.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/offline/json_cache.dart';

/// Read-only per-project board cache (Section 14.2: "cache of the last
/// overview and board"; MT-5.6-03 applies MT-5.6-01's caching pattern
/// with no new semantics).
///
/// Tasks round-trip through the generated serializers (NFR-11 discipline:
/// the schema owns the wire shape, including the canonical [StateEnum]
/// spellings — no hand-built task JSON anywhere).
class BoardCache {
  BoardCache(this._cache);

  final JsonCache _cache;

  static String _key(String projectId) => 'board_tasks_cache_v1:$projectId';

  Future<List<Task>?> read(String projectId) async {
    try {
      final String? raw = await _cache.read(_key(projectId));
      if (raw == null) {
        return null;
      }
      final Object? decoded = jsonDecode(raw);
      if (decoded is! List) {
        return null;
      }
      final List<Task> tasks = <Task>[];
      for (final Object? item in decoded) {
        if (item is! Map) {
          continue;
        }
        tasks.add(
          standardSerializers.deserialize(
            item,
            specifiedType: const FullType(Task),
          )! as Task,
        );
      }
      return tasks;
    } catch (_) {
      // Corrupt cache entry: treat as absent, never crash the board.
      return null;
    }
  }

  Future<void> write(String projectId, List<Task> tasks) async {
    try {
      await _cache.write(
        _key(projectId),
        jsonEncode(<Object?>[
          for (final Task task in tasks)
            standardSerializers.serialize(
              task,
              specifiedType: const FullType(Task),
            ),
        ]),
      );
    } catch (_) {
      // Cache write failure only costs the next offline read.
    }
  }
}

final Provider<BoardCache> boardCacheProvider = Provider<BoardCache>(
  (Ref ref) => BoardCache(ref.watch(jsonCacheProvider)),
);
