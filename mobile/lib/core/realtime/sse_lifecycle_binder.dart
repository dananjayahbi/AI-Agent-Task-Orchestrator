import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../security/auth_gate.dart';
import 'realtime_providers.dart';
import 'sse_client.dart';

/// Binds the SSE client's lifecycle to the app's and the biometric gate's
/// (MT-5.5-05; Section 14.2: "SSE stream when foregrounded; on resume,
/// replay from the last event id").
///
/// * Gate **unlocked** + app **foreground** → [SseClient.start].
/// * Gate locked (cold start, inactivity timeout, AUTH_REQUIRED discard) or
///   app paused/detached → [SseClient.pause] — a locked app never holds an
///   authenticated stream open (Section 14.2, release contract).
///
/// Invisible infrastructure: mounts once around the app shell.
class SseLifecycleBinder extends ConsumerStatefulWidget {
  const SseLifecycleBinder({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<SseLifecycleBinder> createState() => _SseLifecycleBinderState();
}

class _SseLifecycleBinderState extends ConsumerState<SseLifecycleBinder>
    with WidgetsBindingObserver {
  AppLifecycleState _lifecycle = AppLifecycleState.resumed;

  /// The client once this binder has started it — kept as a local reference
  /// so a never-started binder never constructs `sseClientProvider` (and its
  /// config-dependent API client) in pass-through flows.
  SseClient? _startedClient;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    setState(() => _lifecycle = state);
    _sync();
  }

  @override
  Widget build(BuildContext context) {
    // Re-run the sync whenever the gate state changes.
    ref.watch(authGateProvider);
    // Defer to after this frame so start/pause never happens mid-build.
    Future<void>.microtask(_sync);
    return widget.child;
  }

  void _sync() {
    if (!mounted) {
      return;
    }
    final bool shouldRun =
        ref.read(authGateProvider).status == GateStatus.unlocked &&
            _lifecycle == AppLifecycleState.resumed;
    if (shouldRun) {
      _startedClient ??= ref.read(sseClientProvider);
      if (!_startedClient!.isRunning) {
        // Fire-and-forget: the client loop owns its own error handling.
        _startedClient!.start();
      }
    } else if (_startedClient != null && _startedClient!.isRunning) {
      _startedClient!.pause();
    }
  }
}
