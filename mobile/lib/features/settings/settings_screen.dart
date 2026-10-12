import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../core/widgets/placeholder_view.dart';

/// Settings area (parent plan Section 14.1): device info, biometric toggle,
/// logout, server selection — later mobile WPs.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: const PlaceholderView(
        area: AppArea.settings,
        landsIn: 'WP-5.5 MT-5.5-04 and later mobile WPs',
        plan: 'Device info, biometric toggle, logout and server selection.',
      ),
    );
  }
}
