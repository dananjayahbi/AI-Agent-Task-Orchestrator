import 'package:flutter/material.dart';

/// Theme baseline for the app (parent plan Section 14.3).
///
/// One seed color drives both light and dark schemes; feature WPs refine
/// component themes on top of this baseline rather than restyling per screen.
abstract final class AppTheme {
  static const Color _seed = Color(0xFF3559C7);

  static ThemeData light() => _base(Brightness.light);

  static ThemeData dark() => _base(Brightness.dark);

  static ThemeData _base(Brightness brightness) {
    final ColorScheme scheme = ColorScheme.fromSeed(
      seedColor: _seed,
      brightness: brightness,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      navigationBarTheme: NavigationBarThemeData(
        indicatorColor: scheme.secondaryContainer,
      ),
    );
  }
}
