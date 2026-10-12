import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'onboarding_biometric_enrollment_step.dart';
import 'onboarding_device_registration_step.dart';
import 'onboarding_flow.dart';
import 'onboarding_login_step.dart';
import 'onboarding_server_url_step.dart';

/// Container for the four Section 14.1 onboarding screens (MT-5.5-06),
/// rendered by [LockGate] while onboarding needs screen time.
///
/// The step comes from [onboardingFlowProvider] — the single source of
/// flow state (Section 14.3) — so a restored session resumes on the right
/// screen. Step widgets own only their local form state.
class OnboardingScreen extends ConsumerWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final OnboardingState state = ref.watch(onboardingFlowProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Onboarding'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(24),
          child: Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              'Step ${state.step.index + 1} of ${OnboardingStep.values.length}'
              ' — ${state.step.title}',
              key: const ValueKey<String>('onboarding-progress-label'),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: switch (state.step) {
              OnboardingStep.serverUrl => const OnboardingServerUrlStep(),
              OnboardingStep.login => const OnboardingLoginStep(),
              OnboardingStep.deviceRegistration =>
                const OnboardingDeviceRegistrationStep(),
              OnboardingStep.biometricEnrollment =>
                const OnboardingBiometricEnrollmentStep(),
            },
          ),
        ),
      ),
    );
  }
}
