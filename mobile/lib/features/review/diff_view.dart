import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/read_error_messages.dart';
import 'diff_parser.dart';
import 'diff_providers.dart';
import 'rule_results_view.dart';

/// Per-file line cap (Section 14.2 "size-capped"): a pathological file
/// renders at most this many lines at once and collapses the rest
/// behind "Show more" (RISK-13 discipline). Recorded in the WP
/// changelog.
const int diffPerFileLineLimit = 400;

/// Single-line truncation threshold: longer monospace lines render cut
/// with a continuation ellipsis instead of an unbounded widget
/// (MT-5.8-03 risk note — the threshold is recorded in the changelog).
const int diffLineTruncationLimit = 2000;

/// Fixed region height, mirroring the task-detail screen's fixed-height
/// checkpoint stream: the diff region owns its own vertical scroll so
/// the file list can be genuinely lazy (a shrink-wrapped list would
/// build every file up front — exactly what Section 14.2 forbids).
const double diffRegionHeight = 420;

/// Minimal keyword maps by file extension — the plan explicitly keeps
/// the grammars light and relies on the plain fallback (MT-5.8-03 risk
/// note: adding grammars is a dependency decision, not silent scope).
const Map<String, Set<String>> _keywordsByExtension = <String, Set<String>>{
  'dart': <String>{
    'abstract',
    'as',
    'async',
    'await',
    'break',
    'case',
    'catch',
    'class',
    'const',
    'continue',
    'default',
    'do',
    'else',
    'enum',
    'export',
    'extends',
    'external',
    'factory',
    'false',
    'final',
    'finally',
    'for',
    'get',
    'if',
    'implements',
    'import',
    'in',
    'is',
    'late',
    'mixin',
    'new',
    'null',
    'on',
    'part',
    'required',
    'rethrow',
    'return',
    'set',
    'static',
    'super',
    'switch',
    'this',
    'throw',
    'true',
    'try',
    'typedef',
    'var',
    'void',
    'while',
    'with',
    'yield',
  },
  'kt': <String>{
    'class',
    'object',
    'interface',
    'package',
    'import',
    'return',
    'if',
    'else',
    'for',
    'while',
    'when',
    'is',
    'in',
    'null',
    'true',
    'false',
    'this',
    'super',
    'override',
    'private',
    'public',
    'internal',
    'fun',
    'val',
    'var',
    'companion',
    'data',
    'sealed',
    'suspend',
  },
  'java': <String>{
    'abstract',
    'boolean',
    'break',
    'byte',
    'case',
    'catch',
    'char',
    'class',
    'continue',
    'default',
    'do',
    'double',
    'else',
    'enum',
    'extends',
    'false',
    'final',
    'finally',
    'float',
    'for',
    'if',
    'implements',
    'import',
    'instanceof',
    'int',
    'interface',
    'long',
    'new',
    'null',
    'package',
    'private',
    'protected',
    'public',
    'return',
    'short',
    'static',
    'super',
    'switch',
    'this',
    'throw',
    'throws',
    'true',
    'try',
    'void',
    'while',
  },
  'js': <String>{
    'async',
    'await',
    'break',
    'case',
    'catch',
    'class',
    'const',
    'continue',
    'default',
    'delete',
    'do',
    'else',
    'export',
    'extends',
    'false',
    'finally',
    'for',
    'from',
    'function',
    'if',
    'import',
    'in',
    'instanceof',
    'let',
    'new',
    'null',
    'return',
    'super',
    'switch',
    'this',
    'throw',
    'true',
    'try',
    'typeof',
    'undefined',
    'var',
    'void',
    'while',
    'yield',
  },
  'ts': <String>{
    'abstract',
    'any',
    'as',
    'async',
    'await',
    'boolean',
    'break',
    'case',
    'catch',
    'class',
    'const',
    'continue',
    'default',
    'delete',
    'else',
    'enum',
    'export',
    'extends',
    'false',
    'finally',
    'for',
    'from',
    'function',
    'if',
    'implements',
    'import',
    'in',
    'instanceof',
    'interface',
    'keyof',
    'let',
    'namespace',
    'never',
    'new',
    'null',
    'number',
    'override',
    'private',
    'protected',
    'public',
    'readonly',
    'return',
    'string',
    'super',
    'switch',
    'this',
    'throw',
    'true',
    'try',
    'type',
    'typeof',
    'undefined',
    'unknown',
    'var',
    'void',
    'while',
  },
  'py': <String>{
    'and',
    'as',
    'assert',
    'async',
    'await',
    'break',
    'class',
    'continue',
    'def',
    'del',
    'elif',
    'else',
    'except',
    'False',
    'finally',
    'for',
    'from',
    'global',
    'if',
    'import',
    'in',
    'is',
    'lambda',
    'None',
    'nonlocal',
    'not',
    'or',
    'pass',
    'raise',
    'return',
    'True',
    'try',
    'while',
    'with',
    'yield',
  },
  'go': <String>{
    'break',
    'case',
    'chan',
    'const',
    'continue',
    'default',
    'defer',
    'else',
    'fallthrough',
    'for',
    'func',
    'go',
    'goto',
    'if',
    'import',
    'interface',
    'map',
    'nil',
    'package',
    'range',
    'return',
    'select',
    'struct',
    'switch',
    'type',
    'var',
    'true',
    'false',
  },
  'rs': <String>{
    'as',
    'async',
    'await',
    'break',
    'const',
    'continue',
    'crate',
    'dyn',
    'else',
    'enum',
    'extern',
    'false',
    'fn',
    'for',
    'if',
    'impl',
    'in',
    'let',
    'loop',
    'match',
    'mod',
    'move',
    'mut',
    'pub',
    'ref',
    'return',
    'self',
    'Self',
    'static',
    'struct',
    'super',
    'trait',
    'true',
    'type',
    'unsafe',
    'use',
    'where',
    'while',
  },
  'sh': <String>{
    'case',
    'do',
    'done',
    'elif',
    'else',
    'esac',
    'exit',
    'export',
    'fi',
    'for',
    'function',
    'if',
    'in',
    'local',
    'return',
    'then',
    'unset',
    'while',
  },
};

/// Keyword set for [path]'s extension; empty = plain fallback (never a
/// wrong grammar — MT-5.8-03).
Set<String> keywordsForExtension(String path) {
  final String name = path.split('/').last;
  final int dot = name.lastIndexOf('.');
  if (dot <= 0) {
    return const <String>{};
  }
  final String ext = name.substring(dot + 1).toLowerCase();
  return _keywordsByExtension[ext] ?? const <String>{};
}

/// Split one diff line into (text, isKeyword) spans; comment-shaped
/// lines render as one comment span. Pure — unit-tested directly.
List<(String, bool)> highlightLine(String line, Set<String> keywords) {
  final String trimmed = line.trimLeft();
  if (keywords.isNotEmpty &&
      (trimmed.startsWith('//') ||
          trimmed.startsWith('#') ||
          trimmed.startsWith('/*'))) {
    return <(String, bool)>[(line, false)];
  }
  final List<(String, bool)> parts = <(String, bool)>[];
  final RegExp word = RegExp(r'\w+');
  int cursor = 0;
  for (final Match match in word.allMatches(line)) {
    if (match.start > cursor) {
      parts.add((line.substring(cursor, match.start), false));
    }
    final String token = match.group(0)!;
    parts.add((token, keywords.contains(token)));
    cursor = match.end;
  }
  if (cursor < line.length) {
    parts.add((line.substring(cursor), false));
  }
  return parts;
}

/// The diff region of the review sheet (MT-5.8-03): fetch-once patch,
/// per-file lazy rendering, size caps, monospace with per-file
/// horizontal scroll, minimal keyword highlighting, the Section 9.7
/// marker on stats-only payloads, and backend-authoritative stats (the
/// renderer never recomputes them).
class DiffRegionView extends ConsumerStatefulWidget {
  const DiffRegionView({
    super.key,
    required this.resolution,
    this.lineLimit = diffPerFileLineLimit,
  });

  /// The resolution whose patch is rendered — also the source of the
  /// authoritative stats (Section 9.7).
  final Resolution resolution;

  /// Overridable per-file line cap (small caps keep widget tests fast).
  final int lineLimit;

  @override
  ConsumerState<DiffRegionView> createState() => _DiffRegionViewState();
}

class _DiffRegionViewState extends ConsumerState<DiffRegionView> {
  final ScrollController _controller = ScrollController();

  /// Per-file currently-shown line counts (starts at the cap, grows by
  /// the cap on each "Show more").
  final Map<int, int> _shown = <int, int>{};
  int _targetIndex = 0;

  @override
  void didUpdateWidget(DiffRegionView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.resolution.id != widget.resolution.id) {
      // A different patch — reset the per-patch UI state honestly
      // (a re-pinned resolution never inherits the old cap/expansion).
      _shown.clear();
      _targetIndex = 0;
      if (_controller.hasClients) {
        _controller.jumpTo(0);
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _jumpTo(int index, int count) {
    setState(() => _targetIndex = index);
    if (count <= 1 || !_controller.hasClients) {
      return;
    }
    final ScrollPosition position = _controller.position;
    final double max = position.maxScrollExtent;
    if (max <= 0) {
      return;
    }
    _controller.jumpTo(max * index / (count - 1));
  }

  @override
  Widget build(BuildContext context) {
    final DiffState state = ref.watch(diffProvider(widget.resolution.id));
    switch (state.status) {
      case DiffStatus.loading:
        return SizedBox(
          key: const ValueKey<String>('review-diff-loading'),
          height: diffRegionHeight,
          child: const Center(child: CircularProgressIndicator()),
        );
      case DiffStatus.error:
        return SizedBox(
          key: const ValueKey<String>('review-diff-error'),
          height: diffRegionHeight,
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Text(
                    friendlyReadErrorMessage(state.error!),
                    textAlign: TextAlign.center,
                  ),
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  key: const ValueKey<String>('review-diff-retry'),
                  onPressed: () => ref
                      .read(diffProvider(widget.resolution.id).notifier)
                      .load(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Try again'),
                ),
              ],
            ),
          ),
        );
      case DiffStatus.ready:
        return _ready(context, state.patch!);
    }
  }

  Widget _ready(BuildContext context, PatchPayloadResult result) {
    final ThemeData theme = Theme.of(context);
    return ReviewSectionCard(
      title: 'Diff',
      // The stats-only path carries its own authoritative stats block;
      // showing them twice in one card would be noise.
      trailing: result is ParsedPatchResult
          ? Text(
              key: const ValueKey<String>('review-diff-stats'),
              diffStatsLabel(widget.resolution),
              style: theme.textTheme.labelSmall
                  ?.copyWith(color: theme.colorScheme.outline),
            )
          : null,
      child: switch (result) {
        NoBodyPatchResult() => _markerView(context, result.marker),
        ParsedPatchResult() => _parsedView(context, result.patch),
      },
    );
  }

  /// Section 9.7's shared marker path: phrase + authoritative stats +
  /// the backend's own file list — never fabricated content.
  Widget _markerView(BuildContext context, String marker) {
    final ThemeData theme = Theme.of(context);
    final List<String> files = widget.resolution.changedFiles.toList();
    return SizedBox(
      key: const ValueKey<String>('review-diff-marker'),
      height: diffRegionHeight,
      child: ListView(
        padding: EdgeInsets.zero,
        children: <Widget>[
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: theme.colorScheme.errorContainer,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              marker,
              key: const ValueKey<String>('review-diff-marker-phrase'),
              style: theme.textTheme.titleMedium?.copyWith(
                color: theme.colorScheme.onErrorContainer,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            diffStatsLabel(widget.resolution),
            key: const ValueKey<String>('review-diff-marker-stats'),
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 8),
          Text('Changed files', style: theme.textTheme.titleSmall),
          for (final String file in files)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Text(
                file,
                style: theme.textTheme.bodySmall
                    ?.copyWith(fontFamily: 'monospace'),
              ),
            ),
        ],
      ),
    );
  }

  Widget _parsedView(BuildContext context, ParsedPatch patch) {
    final ThemeData theme = Theme.of(context);
    if (patch.files.isEmpty && patch.opaque.isEmpty) {
      return SizedBox(
        key: const ValueKey<String>('review-diff-empty'),
        height: diffRegionHeight,
        child: Center(
          child: Text(
            'No file changes in this patch.',
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: theme.colorScheme.outline),
          ),
        ),
      );
    }

    final int opaqueCount = patch.opaque.isEmpty ? 0 : 1;
    final int count = patch.files.length;
    final int navCount = count;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Row(
          children: <Widget>[
            IconButton(
              key: const ValueKey<String>('review-diff-prev-file'),
              tooltip: 'Previous file',
              onPressed: _targetIndex > 0 && navCount > 1
                  ? () => _jumpTo(_targetIndex - 1, navCount)
                  : null,
              icon: const Icon(Icons.chevron_left),
            ),
            Text(
              navCount == 0
                  ? 'Plain patch text'
                  : 'File ${_targetIndex + 1} of $navCount',
              key: const ValueKey<String>('review-diff-file-position'),
              style: theme.textTheme.labelMedium,
            ),
            const Spacer(),
            IconButton(
              key: const ValueKey<String>('review-diff-next-file'),
              tooltip: 'Next file',
              onPressed: _targetIndex < navCount - 1 && navCount > 1
                  ? () => _jumpTo(_targetIndex + 1, navCount)
                  : null,
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
        SizedBox(
          key: const ValueKey<String>('review-diff-scroll'),
          height: diffRegionHeight,
          child: ListView.builder(
            controller: _controller,
            // Only the visible file cards are ever built — the point of
            // Section 14.2's "lazy-loaded per file" (no cache window to
            // pre-build offscreen files either).
            cacheExtent: 0,
            itemCount: count + opaqueCount,
            itemBuilder: (BuildContext context, int index) {
              if (index >= count) {
                return _opaqueCard(context, patch.opaque);
              }
              return _fileCard(context, index, patch.files[index]);
            },
          ),
        ),
      ],
    );
  }

  Widget _opaqueCard(BuildContext context, List<String> opaque) {
    final ThemeData theme = Theme.of(context);
    return Container(
      key: const ValueKey<String>('review-diff-opaque'),
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Unrecognized patch text (shown as-is)',
              style: theme.textTheme.labelMedium),
          const SizedBox(height: 6),
          Text(
            opaque.join('\n'),
            style: theme.textTheme.bodySmall?.copyWith(fontFamily: 'monospace'),
          ),
        ],
      ),
    );
  }

  Widget _fileCard(BuildContext context, int index, PatchFile file) {
    final ThemeData theme = Theme.of(context);
    final Set<String> keywords = keywordsForExtension(file.path);
    final List<PatchLine> allLines = <PatchLine>[];
    final List<String> headers = <String>[];
    for (final PatchHunk hunk in file.hunks) {
      headers.add(hunk.header);
      allLines.addAll(hunk.lines);
    }
    final int lineCount = allLines.length + file.opaque.length + headers.length;
    final int shown = _shown[index] ?? widget.lineLimit;
    final bool capped = lineCount > shown;

    final List<Widget> body = <Widget>[];
    for (final String header in headers) {
      body.add(_lineRow(
        symbol: '@',
        tint: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.4),
        line: header,
        keywords: const <String>{},
        comment: false,
        monospaceTheme: theme,
      ));
    }
    for (final PatchLine line in allLines
        .take(shown - headers.length < 0 ? 0 : shown - headers.length)) {
      final bool isComment = keywords.isNotEmpty &&
          (line.content.trimLeft().startsWith('//') ||
              line.content.trimLeft().startsWith('#') ||
              line.content.trimLeft().startsWith('/*'));
      body.add(_lineRow(
        symbol: line.kind == PatchLineKind.add
            ? '+'
            : line.kind == PatchLineKind.del
                ? '-'
                : ' ',
        tint: line.kind == PatchLineKind.add
            ? theme.colorScheme.primaryContainer.withValues(alpha: 0.35)
            : line.kind == PatchLineKind.del
                ? theme.colorScheme.errorContainer.withValues(alpha: 0.35)
                : Colors.transparent,
        line: line.content,
        keywords: keywords,
        comment: isComment,
        monospaceTheme: theme,
      ));
    }
    for (final String opaqueLine in file.opaque.take(
        shown - headers.length - allLines.length < 0
            ? 0
            : shown - headers.length - allLines.length)) {
      body.add(_lineRow(
        symbol: ' ',
        tint: Colors.transparent,
        line: opaqueLine,
        keywords: const <String>{},
        comment: false,
        monospaceTheme: theme,
      ));
    }

    return Container(
      key: ValueKey<String>('review-diff-file-${file.path}'),
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            key: ValueKey<String>('review-diff-file-header-${file.path}'),
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            color: theme.colorScheme.surfaceContainerHighest,
            child: Text(
              '${file.path}${file.oldPath != null && file.oldPath != file.path ? ' (from ${file.oldPath})' : ''}'
              ' · ${file.status.name}',
              style: theme.textTheme.labelMedium
                  ?.copyWith(fontFamily: 'monospace'),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          // Per-file horizontal scroll only — no page-level horizontal
          // scrolling anywhere (Section 14.2).
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const AlwaysScrollableScrollPhysics(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: body,
            ),
          ),
          if (capped)
            TextButton(
              key: ValueKey<String>('review-diff-show-more-${file.path}'),
              onPressed: () => setState(() {
                _shown[index] = shown + widget.lineLimit;
              }),
              child: Text(
                'Show more (${lineCount - shown} lines hidden)',
              ),
            ),
        ],
      ),
    );
  }

  Widget _lineRow({
    required String symbol,
    required Color tint,
    required String line,
    required Set<String> keywords,
    required bool comment,
    required ThemeData monospaceTheme,
  }) {
    final String content = line.length > diffLineTruncationLimit
        ? '${line.substring(0, diffLineTruncationLimit)}…'
        : line;
    final TextStyle base = TextStyle(
      fontFamily: 'monospace',
      fontSize: 12,
      height: 1.45,
      color: monospaceTheme.colorScheme.onSurface,
    );
    final TextStyle commentStyle = base.copyWith(
      color: monospaceTheme.colorScheme.outline,
      fontStyle: FontStyle.italic,
    );
    final TextStyle keywordStyle = base.copyWith(
      color: monospaceTheme.colorScheme.primary,
      fontWeight: FontWeight.w600,
    );
    return Container(
      color: tint,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 18,
            child: Text(
              symbol,
              style: base.copyWith(color: monospaceTheme.colorScheme.outline),
            ),
          ),
          Text.rich(
            TextSpan(
              children: comment
                  ? <InlineSpan>[TextSpan(text: content, style: commentStyle)]
                  : _highlightSpans(content, keywords, base, keywordStyle),
            ),
            maxLines: 1,
            softWrap: false,
            style: base,
          ),
        ],
      ),
    );
  }

  static List<InlineSpan> _highlightSpans(
    String content,
    Set<String> keywords,
    TextStyle base,
    TextStyle keywordStyle,
  ) {
    if (keywords.isEmpty) {
      return <InlineSpan>[TextSpan(text: content, style: base)];
    }
    final List<InlineSpan> spans = <InlineSpan>[];
    for (final (String, bool) part in highlightLine(content, keywords)) {
      spans.add(
        TextSpan(
          text: part.$1,
          style: part.$2 ? keywordStyle : base,
        ),
      );
    }
    return spans;
  }
}

/// Backend-authoritative diff stats for [resolution] (Section 9.7) —
/// read from the resolution's `diff_summary` / `changed_files`, never
/// recomputed from the parsed patch (shared by the diff region and the
/// approve confirmation, MT-5.8-04 risk note).
String diffStatsLabel(Resolution resolution) {
  final List<String> files = resolution.changedFiles.toList();
  final Object? summary = resolution.diffSummary?.value;
  if (summary is! Map<Object?, Object?>) {
    return '${files.length} ${files.length == 1 ? 'file' : 'files'}';
  }
  final Object? insertions = summary['insertions'];
  final Object? deletions = summary['deletions'];
  final String counts = (insertions is num && deletions is num)
      ? '+${insertions.toInt()} −${deletions.toInt()}'
      : '';
  final String base = '${files.length} ${files.length == 1 ? 'file' : 'files'}';
  return counts.isEmpty ? base : '$base · $counts';
}
