import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../core/widgets/placeholder_view.dart';

/// Notifications area (parent plan Section 14.1): alert history with
/// per-event-type toggles — WP-5.9 (MT-5.9-03, deferred).
///
/// The audit log entry point lives here, beside Notifications
/// (MT-5.9-04, Section 14.1): the tab is the discovery surface the
/// plan puts next to it, while the history itself stays an honest
/// placeholder until WP-5.9's first slice lands.
class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: Column(
        children: <Widget>[
          const Expanded(
            child: PlaceholderView(
              area: AppArea.notifications,
              landsIn: 'WP-5.9',
              plan: 'Alert history and per-event-type toggles.',
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
            child: SizedBox(
              width: double.infinity,
              child: FilledButton.tonalIcon(
                key: const ValueKey<String>('notifications-audit-log-entry'),
                onPressed: () =>
                    Navigator.pushNamed(context, AppArea.auditLog.path),
                icon: const Icon(Icons.history),
                label: const Text('Open audit log'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
