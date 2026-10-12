import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../core/widgets/placeholder_view.dart';

/// Notifications area (parent plan Section 14.1): alert history with
/// per-event-type toggles — WP-5.9.
class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: const PlaceholderView(
        area: AppArea.notifications,
        landsIn: 'WP-5.9',
        plan: 'Alert history and per-event-type toggles.',
      ),
    );
  }
}
