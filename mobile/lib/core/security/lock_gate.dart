import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/onboarding/onboarding_screen.dart';
import 'auth_gate.dart';
import 'biometric_authenticator.dart';

/// App-level lock (MT-5.5-04; Section 14.2): while the gate is locked, the
/// authenticated shell is replaced by [LockedView] — no authenticated data
/// is built or shown underneath. Cold start and the inactivity timeout both
/// land here.
///
/// MT-5.5-06 routing: when the onboarding flow needs screen time
/// ([onboardingRequiredProvider] — fresh install, mid-flow resume, or
/// post-revocation re-entry), it is what renders instead of the shell or
/// the lock view; the onboarding screens carry no authenticated data, so
/// the lock guarantee is preserved. Once onboarding completes the flag
/// clears and the lock view rules alone.
///
/// Taps anywhere in the unlocked app are forwarded to
/// [AuthGateNotifier.noteActivity] so the inactivity countdown resets on
/// real user interaction (Section 14.2).
class LockGate extends ConsumerWidget {
  const LockGate({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AuthGateState gate = ref.watch(authGateProvider);
    final bool onboarding = ref.watch(onboardingRequiredProvider);
    switch (gate.status) {
      case GateStatus.initializing:
        return const _GateLoadingView();
      case GateStatus.noCredential:
        // No stored credential: onboarding territory (fresh install or
        // post-revocation re-entry, release contract). Without pending
        // onboarding the unauthenticated shell passes through.
        return onboarding ? const OnboardingScreen() : child;
      case GateStatus.locked:
        // The enrollment step of onboarding runs under a locked gate (the
        // device token was just stored and stays unreleased — Section 12.2).
        if (onboarding) {
          return const OnboardingScreen();
        }
        return LockedView(state: gate);
      case GateStatus.unlocked:
        return Listener(
          behavior: HitTestBehavior.translucent,
          onPointerDown: (_) =>
              ref.read(authGateProvider.notifier).noteActivity(),
          child: child,
        );
      case GateStatus.storageError:
        return const LockedView(
            state: AuthGateState(status: GateStatus.storageError));
    }
  }
}

class _GateLoadingView extends StatelessWidget {
  const _GateLoadingView();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}

/// The locked screen: unlock affordance plus honest per-state messaging —
/// enrollment guidance when nothing is enrolled (never a silent bypass),
/// an honest limitation note when the device cannot do OS authentication,
/// and a retry when secure storage was unreadable (Section 14.2).
class LockedView extends ConsumerWidget {
  const LockedView({super.key, required this.state});

  final AuthGateState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ThemeData theme = Theme.of(context);
    final AuthGateNotifier gate = ref.read(authGateProvider.notifier);

    final bool storageFailed = state.status == GateStatus.storageError;
    final bool noEnrollment =
        state.availability == BiometricAvailability.enrollmentRequired;
    final bool unsupported =
        state.availability == BiometricAvailability.unsupported;

    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(
                Icons.lock_outline,
                size: 48,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                storageFailed
                    ? 'Could not read secure storage'
                    : 'Orchestrator is locked',
                style: theme.textTheme.titleLarge,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                storageFailed
                    ? 'The device credential store could not be read. '
                        'Try again — nothing is unlocked until it can be verified.'
                    : 'Unlock with biometrics (or your device passcode) to '
                        'continue.',
                style: theme.textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              if (noEnrollment) ...<Widget>[
                const SizedBox(height: 8),
                Text(
                  'No biometrics are enrolled on this device. Enroll a '
                  'fingerprint or face (or set a device passcode) in system '
                  'settings, then unlock here. The app does not bypass this '
                  'step.',
                  style: theme.textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
              ],
              if (unsupported) ...<Widget>[
                const SizedBox(height: 8),
                Text(
                  'This device does not support biometric or passcode '
                  'unlock, which this app requires (documented limitation).',
                  style: theme.textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
              ],
              if (state.lastUnlockFailed) ...<Widget>[
                const SizedBox(height: 8),
                Text(
                  'Not recognized. Try again.',
                  style: theme.textTheme.bodySmall
                      ?.copyWith(color: theme.colorScheme.error),
                  textAlign: TextAlign.center,
                ),
              ],
              const SizedBox(height: 24),
              if (storageFailed)
                FilledButton.icon(
                  onPressed: gate.retryProbe,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Try again'),
                )
              else if (!unsupported)
                FilledButton.icon(
                  onPressed: () => gate.unlock(),
                  icon: const Icon(Icons.lock_open_outlined),
                  label: const Text('Unlock'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
