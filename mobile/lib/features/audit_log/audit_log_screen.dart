import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../core/widgets/placeholder_view.dart';

/// Audit log area (parent plan Section 14.1): read-only list with
/// filters — WP-5.9.
class AuditLogScreen extends StatelessWidget {
  const AuditLogScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Audit log')),
      body: const PlaceholderView(
        area: AppArea.auditLog,
        landsIn: 'WP-5.9',
        plan: 'Read-only audit log list with filters.',
      ),
    );
  }
}
