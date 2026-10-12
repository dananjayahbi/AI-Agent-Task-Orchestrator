import 'package:flutter/material.dart';

import '../../app/routes.dart';

/// Honest empty placeholder for a Section 14.1 area that a later work package
/// implements (parent plan Section 20.3 state discipline: no mocked business
/// data pretending to be real — the screen says plainly that it is empty).
class PlaceholderView extends StatelessWidget {
  const PlaceholderView({
    super.key,
    required this.area,
    required this.landsIn,
    this.plan,
  });

  /// The Section 14.1 area this placeholder stands in for.
  final AppArea area;

  /// Work package or micro-task that will implement the real screen.
  final String landsIn;

  /// Optional one-line description of what the real screen will contain.
  final String? plan;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(
              Icons.construction_outlined,
              size: 48,
              color: theme.colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              'Not implemented yet — lands in $landsIn.',
              textAlign: TextAlign.center,
              style: theme.textTheme.titleMedium,
            ),
            if (plan != null) ...<Widget>[
              const SizedBox(height: 8),
              Text(plan!, textAlign: TextAlign.center),
            ],
            const SizedBox(height: 8),
            Text(
              'Nothing is loaded and no data is shown until then.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.outline),
            ),
          ],
        ),
      ),
    );
  }
}
