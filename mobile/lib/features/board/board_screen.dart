import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../core/widgets/placeholder_view.dart';

/// Board area (parent plan Section 14.1): project selector, horizontally
/// paged state columns, pull to refresh, live updates — WP-5.6.
class BoardScreen extends StatelessWidget {
  const BoardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Board')),
      body: const PlaceholderView(
        area: AppArea.board,
        landsIn: 'WP-5.6',
        plan: 'Project selector and horizontally paged six-state columns '
            'with pull to refresh.',
      ),
    );
  }
}
