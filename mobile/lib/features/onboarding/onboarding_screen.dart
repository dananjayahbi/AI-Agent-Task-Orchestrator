import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../core/widgets/placeholder_view.dart';

/// Onboarding area (parent plan Section 14.1): server URL entry, login,
/// device registration, biometric enrollment — implemented in MT-5.5-06.
class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Onboarding')),
      body: const PlaceholderView(
        area: AppArea.onboarding,
        landsIn: 'MT-5.5-06',
        plan: 'Server URL entry, Owner login, device registration and '
            'biometric enrollment.',
      ),
    );
  }
}
