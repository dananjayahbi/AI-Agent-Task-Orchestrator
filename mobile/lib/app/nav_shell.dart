import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'routes.dart';

/// Index of the visible tab inside the navigation shell.
///
/// Riverpod is the single state-management pattern of this app (parent plan
/// Section 6.6); the shell selection is deliberately modeled as a provider so
/// later WPs can deep-link into a tab without bespoke plumbing.
class ShellIndexNotifier extends Notifier<int> {
  @override
  int build() => 0;

  void select(int index) => state = index;
}

final shellIndexProvider = NotifierProvider<ShellIndexNotifier, int>(
  ShellIndexNotifier.new,
);

/// Bottom-navigation destinations of the shell: the four Section 14.1 tab
/// areas. The other areas (onboarding, task detail, review, audit log) are
/// pushed as routes from [routes.dart].
class _Tab {
  const _Tab(this.area, this.icon, this.navLabel);

  final AppArea area;
  final IconData icon;
  final String navLabel;
}

const List<_Tab> _tabs = <_Tab>[
  _Tab(AppArea.home, Icons.home_outlined, 'Home'),
  _Tab(AppArea.board, Icons.dashboard_outlined, 'Board'),
  _Tab(AppArea.notifications, Icons.notifications_outlined, 'Notifications'),
  _Tab(AppArea.settings, Icons.settings_outlined, 'Settings'),
];

/// Top-level navigation shell hosting the Section 14.1 tab areas.
class NavShell extends ConsumerWidget {
  const NavShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final int index = ref.watch(shellIndexProvider);
    return Scaffold(
      body: IndexedStack(
        index: index,
        children: <Widget>[
          for (final _Tab tab in _tabs) screenForArea(tab.area),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (int next) =>
            ref.read(shellIndexProvider.notifier).select(next),
        destinations: <NavigationDestination>[
          for (final _Tab tab in _tabs)
            NavigationDestination(
              icon: Icon(tab.icon),
              label: tab.navLabel,
            ),
        ],
      ),
    );
  }
}
