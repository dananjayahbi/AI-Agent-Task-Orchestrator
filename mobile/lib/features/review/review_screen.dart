import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../core/widgets/placeholder_view.dart';

/// Review sheet area (parent plan Section 14.1): rule results, execution
/// summary, diff and the three review actions — WP-5.8.
class ReviewScreen extends StatelessWidget {
  const ReviewScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Review sheet')),
      body: const PlaceholderView(
        area: AppArea.review,
        landsIn: 'WP-5.8',
        plan: 'Reason and rule results, auditor notes, syntax-highlighted '
            'diff and approve / request-changes / reassign.',
      ),
    );
  }
}
