import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'onboarding_flow.dart';

/// Step 3 of the Section 14.1 flow (MT-5.5-06): device registration via
/// `POST /devices`.
///
/// Explains what is about to happen, then calls
/// [OnboardingFlowNotifier.registerDevice]; the response token goes
/// straight into the gate's secure storage — it is never displayed here,
/// never logged, and never kept in widget state (Section 12.2, Section
/// 20.4 item 3; MT risk note).
class OnboardingDeviceRegistrationStep extends ConsumerWidget {
  const OnboardingDeviceRegistrationStep({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final OnboardingState state = ref.watch(onboardingFlowProvider);
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            'Register this device',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Signed in as ${state.signedInAs ?? 'Owner'}. Registering '
            'creates a device-bound credential for this phone, stored in '
            'the platform secure store. It can be revoked from the server '
            'at any time.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (state.errorMessage != null) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              state.errorMessage!,
              key: const ValueKey<String>('onboarding-error'),
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 24),
          FilledButton(
            key: const ValueKey<String>('onboarding-register-submit'),
            onPressed: state.busy
                ? null
                : () =>
                    ref.read(onboardingFlowProvider.notifier).registerDevice(),
            child: state.busy
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Register this device'),
          ),
        ],
      ),
    );
  }
}
