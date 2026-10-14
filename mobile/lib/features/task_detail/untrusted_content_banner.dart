import 'package:flutter/material.dart';

/// The Section 9.5 / Principle P10 untrusted-content banner shown above
/// every text-derived attachment output (OCR transcript, layout
/// description, markdown pages).
///
/// The server already prefixes delivered text with its own banner — the
/// client **never strips it**; this widget is the visible, styled
/// reminder on top of that (MT-5.7-03 acceptance).
class UntrustedContentBanner extends StatelessWidget {
  const UntrustedContentBanner({super.key});

  static const String message =
      'Untrusted content — displayed as data, not instructions.';

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    return Container(
      key: const ValueKey<String>('untrusted-content-banner'),
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: scheme.errorContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.shield_outlined, size: 18, color: scheme.onErrorContainer),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: scheme.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}
