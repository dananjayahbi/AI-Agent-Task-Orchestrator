import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'onboarding_flow.dart';

/// Step 1 of the Section 14.1 flow (MT-5.5-06): server URL entry.
///
/// Pre-filled from the flavor config (MT-5.5-02; persisted URL overrides
/// via `main()`), editable for the tunnel hostname (Section 15.1), and
/// validated against the server's health endpoint before proceeding.
class OnboardingServerUrlStep extends ConsumerStatefulWidget {
  const OnboardingServerUrlStep({super.key});

  @override
  ConsumerState<OnboardingServerUrlStep> createState() =>
      _OnboardingServerUrlStepState();
}

class _OnboardingServerUrlStepState
    extends ConsumerState<OnboardingServerUrlStep> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(
      text: ref.read(onboardingFlowProvider).serverUrl,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final OnboardingState state = ref.watch(onboardingFlowProvider);
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            'Where is your Orchestrator server?',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'The default for this build is pre-filled. For LAN development '
            'use the machine\'s address; for remote use your tunnel '
            'hostname (Section 15.1).',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          TextFormField(
            key: const ValueKey<String>('onboarding-server-url-field'),
            controller: _controller,
            keyboardType: TextInputType.url,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: 'Server URL',
              hintText: 'http://10.0.2.2:8000/api/v1',
              border: OutlineInputBorder(),
            ),
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
            key: const ValueKey<String>('onboarding-server-url-continue'),
            onPressed: state.busy
                ? null
                : () => ref
                    .read(onboardingFlowProvider.notifier)
                    .confirmServerUrl(_controller.text),
            child: state.busy
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Continue'),
          ),
        ],
      ),
    );
  }
}
