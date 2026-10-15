import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/routes.dart';
import '../../core/api/api_exception.dart';
import '../../core/api/read_error_messages.dart';
import 'notification_tap_router.dart';
import 'push_payload.dart';

/// The deep-link destination picker (MT-5.9-01).
///
/// Pushed by `NotificationTapBinder` once the gate is unlocked, it runs the
/// Section 14.2 rule — *fetch, then route* — behind the standard loading
/// state (Section 20.3), and lands on one of three honest outcomes:
///
/// * `in_human_review` → the task's review sheet (replaced underneath);
/// * the task left review / does not exist → the **stale fallback** (the
///   MT-5.9-01 risk note's "clear state with an explanation"): an explained
///   state with a way home, never a broken sheet and never a dead end;
/// * the check failed → an honest error state with retry and a way home
///   (no destination is guessed from an unknown server answer).
///
/// No review content is fetched or rendered here — only the task row needed
/// to decide, and only after unlock (the route cannot exist while locked).
class NotificationTapScreen extends ConsumerStatefulWidget {
  const NotificationTapScreen({super.key, required this.payload});

  /// The parsed payload the tap carried (ids + short title only).
  final PushTapPayload payload;

  @override
  ConsumerState<NotificationTapScreen> createState() =>
      _NotificationTapScreenState();
}

class _NotificationTapScreenState extends ConsumerState<NotificationTapScreen> {
  TapResolution? _resolution;
  bool _resolving = false;

  @override
  void initState() {
    super.initState();
    // Kick off after first build (post-frame), like the review sheet's load.
    WidgetsBinding.instance.addPostFrameCallback((_) => _resolve());
  }

  Future<void> _resolve() async {
    if (_resolving) {
      return;
    }
    setState(() => _resolving = true);
    final TapResolution resolution =
        await ref.read(notificationTapResolverProvider).resolve(widget.payload);
    if (!mounted) {
      return;
    }
    if (resolution.kind == TapResolutionKind.reviewSheet) {
      // The plan's acceptance destination — replace this picker so the
      // sheet is the only lingering route (no "opening…" screen behind it).
      Navigator.of(context).pushReplacementNamed(
        AppRoutes.forArea(AppArea.review),
        arguments: resolution.taskId,
      );
      return;
    }
    setState(() {
      _resolution = resolution;
      _resolving = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final TapResolution? resolution = _resolution;
    if (resolution == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Opening notification')),
        body: const Center(
          key: ValueKey<String>('deeplink-loading'),
          child: CircularProgressIndicator(),
        ),
      );
    }
    if (resolution.kind == TapResolutionKind.stale) {
      return _ExplainedState(
        key: const ValueKey<String>('deeplink-stale'),
        icon: Icons.notifications_none,
        title: 'This notification is no longer actionable',
        body: 'The task behind it is not awaiting review any more — it may '
            'have been decided, reassigned or archived since the alert was '
            'sent. Nothing was changed.',
        primaryLabel: 'Go to home',
        onPrimary: () =>
            Navigator.of(context).pushReplacementNamed(AppRoutes.root),
      );
    }
    // Unreachable is only produced with the failure it carries.
    final OrchestratorApiException error = resolution.error!;
    return _ExplainedState(
      key: const ValueKey<String>('deeplink-error'),
      icon: Icons.cloud_off,
      title: 'Could not open that notification',
      body: friendlyReadErrorMessage(error),
      primaryLabel: 'Try again',
      onPrimary: () {
        setState(() => _resolution = null);
        _resolve();
      },
      secondaryLabel: 'Go to home',
      onSecondary: () =>
          Navigator.of(context).pushReplacementNamed(AppRoutes.root),
    );
  }
}

/// A clear, explained state — the stale-fallback/error presentation shared
/// by this route (no new screen: this route's own state, MT-5.9-01 risk note).
class _ExplainedState extends StatelessWidget {
  const _ExplainedState({
    super.key,
    required this.icon,
    required this.title,
    required this.body,
    required this.primaryLabel,
    required this.onPrimary,
    this.secondaryLabel,
    this.onSecondary,
  });

  final IconData icon;
  final String title;
  final String body;
  final String primaryLabel;
  final VoidCallback onPrimary;
  final String? secondaryLabel;
  final VoidCallback? onSecondary;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Opening notification')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(icon, size: 48, color: theme.colorScheme.outline),
              const SizedBox(height: 16),
              Text(
                title,
                style: theme.textTheme.titleMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                body,
                style: theme.textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton(
                key: const ValueKey<String>('deeplink-explained-primary'),
                onPressed: onPrimary,
                child: Text(primaryLabel),
              ),
              if (secondaryLabel != null) ...<Widget>[
                const SizedBox(height: 12),
                TextButton(
                  key: const ValueKey<String>('deeplink-explained-secondary'),
                  onPressed: onSecondary,
                  child: Text(secondaryLabel!),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
