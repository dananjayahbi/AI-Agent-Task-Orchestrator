import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/security/auth_gate.dart';
import '../../core/security/biometric_authenticator.dart';
import 'onboarding_flow.dart';

/// Step 4 of the Section 14.1 flow (MT-5.5-06): biometric enrollment.
///
/// The device token is already in secure storage (Step 3); this step arms
/// the MT-5.5-04 gate. Enabling runs the real biometric prompt
/// ([AuthGateNotifier.unlock]) — success completes the flow with the gate
/// unlocked. Skip is honest: [OnboardingFlowNotifier.finish] claims
/// nothing, and the app stays locked until a real unlock (Section 14.2 —
/// no silent bypass).
class OnboardingBiometricEnrollmentStep extends ConsumerWidget {
  const OnboardingBiometricEnrollmentStep({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final OnboardingState state = ref.watch(onboardingFlowProvider);
    final AuthGateState gate = ref.watch(authGateProvider);
    final BiometricAvailability availability = gate.availability;

    final String guidance;
    switch (availability) {
      case BiometricAvailability.enrollmentRequired:
        guidance = 'No biometrics are enrolled on this device yet. Enroll a '
            'fingerprint or face in system settings first — you can come '
            'back here, or skip and unlock later with your device '
            'passcode.';
      case BiometricAvailability.unsupported:
        guidance = 'This device does not support biometric or passcode '
            'unlock, which this app requires (documented limitation). '
            'Setup finishes, but the app cannot be unlocked here.';
      case BiometricAvailability.available:
      case BiometricAvailability.unknown:
        guidance = 'Orchestrator unlocks only after biometric success (or '
            'your device passcode). Enable it now, or skip and unlock '
            'when you first open the app.';
    }

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            'Protect the app',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(guidance, style: Theme.of(context).textTheme.bodyMedium),
          if (gate.lastUnlockFailed) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              'Not recognized. Try again or skip for now.',
              key: const ValueKey<String>('onboarding-error'),
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 24),
          if (availability != BiometricAvailability.unsupported)
            FilledButton(
              key: const ValueKey<String>('onboarding-enrollment-enable'),
              onPressed: state.busy
                  ? null
                  : () async {
                      final AuthGateNotifier authGate =
                          ref.read(authGateProvider.notifier);
                      final bool unlocked = await authGate.unlock();
                      // Complete only after real biometric success — a
                      // cancelled prompt leaves the flow (and the gate)
                      // exactly where they were (honest skip rule).
                      if (unlocked && ref.context.mounted) {
                        await ref
                            .read(onboardingFlowProvider.notifier)
                            .finish();
                      }
                    },
              child: state.busy
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Enable biometric unlock'),
            ),
          TextButton(
            key: const ValueKey<String>('onboarding-enrollment-skip'),
            onPressed: state.busy
                ? null
                : () => ref.read(onboardingFlowProvider.notifier).finish(),
            child: const Text('Skip for now'),
          ),
        ],
      ),
    );
  }
}
