import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import 'diff_parser.dart';
import 'review_repository.dart';

/// Screen state of the diff region (Section 20.3 states).
enum DiffStatus { loading, ready, error }

class DiffState {
  const DiffState({
    required this.status,
    this.patch,
    this.resolutionId,
    this.error,
  });

  const DiffState.loading({required String resolutionId})
      : this(status: DiffStatus.loading, resolutionId: resolutionId);

  const DiffState.ready({
    required String resolutionId,
    required PatchPayloadResult patch,
  }) : this(
          status: DiffStatus.ready,
          resolutionId: resolutionId,
          patch: patch,
        );

  const DiffState.error(OrchestratorApiException error)
      : this(status: DiffStatus.error, error: error);

  final DiffStatus status;
  final String? resolutionId;

  /// The interpreted Section 9.7 payload: parsed files or the shared
  /// "diff too large" marker — never a client-side size guess.
  final PatchPayloadResult? patch;
  final OrchestratorApiException? error;
}

/// One patch fetch per resolution id (family) — the diff region loads
/// lazily and independently of the sheet's initial load (Section 14.2:
/// lazy-loaded per file starts with fetching the patch on demand).
class DiffNotifier extends AutoDisposeFamilyNotifier<DiffState, String> {
  late String _resolutionId;
  int _loadToken = 0;

  @override
  DiffState build(String resolutionId) {
    _resolutionId = resolutionId;
    Future<void>.microtask(load);
    return DiffState.loading(resolutionId: resolutionId);
  }

  Future<void> load() async {
    final String resolutionId = _resolutionId;
    final int token = ++_loadToken;
    try {
      final ResolutionPatch patch =
          await ref.read(reviewRepositoryProvider).fetchPatch(resolutionId);
      if (token != _loadToken) {
        return; // Superseded — drop silently.
      }
      state = DiffState.ready(
        resolutionId: resolutionId,
        patch: interpretPatchPayload(
          diffTooLarge: patch.diffTooLarge,
          patch: patch.patch_,
          marker: patch.marker,
        ),
      );
    } on OrchestratorApiException catch (error) {
      if (token != _loadToken) {
        return;
      }
      state = DiffState.error(error);
    }
  }
}

final AutoDisposeNotifierProviderFamily<DiffNotifier, DiffState, String>
    diffProvider =
    AutoDisposeNotifierProviderFamily<DiffNotifier, DiffState, String>(
  DiffNotifier.new,
);
