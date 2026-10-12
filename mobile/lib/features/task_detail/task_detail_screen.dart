import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../core/widgets/placeholder_view.dart';

/// Task detail area (parent plan Section 14.1): summary, criteria,
/// checkpoint stream, resolutions, attachments — WP-5.7.
class TaskDetailScreen extends StatelessWidget {
  const TaskDetailScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Task detail')),
      body: const PlaceholderView(
        area: AppArea.taskDetail,
        landsIn: 'WP-5.7',
        plan: 'Summary, criteria, live checkpoint stream, resolutions and '
            'attachment viewing.',
      ),
    );
  }
}
