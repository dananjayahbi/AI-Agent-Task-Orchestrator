import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'onboarding_flow.dart';

/// Step 2 of the Section 14.1 flow (MT-5.5-06): Owner login via
/// `POST /auth/login`.
///
/// The password field is obscured and its controller lives only for this
/// widget's lifetime; nothing here logs or echoes the password
/// (Section 12.4). Failures show the flow's friendly, catalog-mapped
/// message — never raw server text.
class OnboardingLoginStep extends ConsumerStatefulWidget {
  const OnboardingLoginStep({super.key});

  @override
  ConsumerState<OnboardingLoginStep> createState() =>
      _OnboardingLoginStepState();
}

class _OnboardingLoginStepState extends ConsumerState<OnboardingLoginStep> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
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
            'Sign in as Owner',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Server: ${state.serverUrl}',
            key: const ValueKey<String>('onboarding-login-server'),
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          TextField(
            key: const ValueKey<String>('onboarding-username-field'),
            controller: _usernameController,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: 'Username',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey<String>('onboarding-password-field'),
            controller: _passwordController,
            obscureText: true,
            autocorrect: false,
            enableSuggestions: false,
            decoration: const InputDecoration(
              labelText: 'Password',
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
            key: const ValueKey<String>('onboarding-login-submit'),
            onPressed: state.busy
                ? null
                : () => ref.read(onboardingFlowProvider.notifier).login(
                      username: _usernameController.text,
                      password: _passwordController.text,
                    ),
            child: state.busy
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Sign in'),
          ),
          TextButton(
            key: const ValueKey<String>('onboarding-login-back'),
            onPressed: state.busy
                ? null
                : () =>
                    ref.read(onboardingFlowProvider.notifier).backToServerUrl(),
            child: const Text('Back to server address'),
          ),
        ],
      ),
    );
  }
}
