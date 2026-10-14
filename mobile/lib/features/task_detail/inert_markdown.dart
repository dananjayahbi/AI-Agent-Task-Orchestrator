import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

/// Renders markdown **inertly** (Principle P10): text widgets only — no
/// HTML execution, no script, no link handlers that leave the app. Raw
/// HTML in the source is displayed as text by the underlying renderer's
/// default escaping behavior; tap handlers are deliberately omitted so
/// an untrusted description can never act.
class InertMarkdown extends StatelessWidget {
  const InertMarkdown({super.key, required this.data, this.selectable = true});

  final String data;
  final bool selectable;

  @override
  Widget build(BuildContext context) {
    return MarkdownBody(
      data: data,
      selectable: selectable,
      // No extension set: a conservative CommonMark subset — untrusted
      // input gets minimal interpretation surface (P10).
    );
  }
}
