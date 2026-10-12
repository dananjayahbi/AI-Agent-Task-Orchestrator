import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../core/widgets/placeholder_view.dart';

/// Home / Overview area (parent plan Section 14.1): project cards, velocity,
/// needs-review banner — implemented in WP-5.6.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Home / Overview')),
      body: const PlaceholderView(
        area: AppArea.home,
        landsIn: 'WP-5.6',
        plan: 'Project cards with state counts and velocity, active agents '
            'and the needs-review banner.',
      ),
    );
  }
}
