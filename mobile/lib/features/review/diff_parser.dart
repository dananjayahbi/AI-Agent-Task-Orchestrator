/// Unified-patch parsing for the mobile diff renderer (MT-5.8-03) — a
/// faithful Dart port of the web viewer's parser semantics
/// (`web/lib/diff/parse.ts`, WP-4.7) so both viewers of the same
/// Section 9.7 patch agree file-for-file (risk note: two renderers must
/// not drift). Pure and deterministic (ADR-009).
library;

/// Section 9.7's verbatim marker phrase — identical to the web viewer's
/// `DIFF_TOO_LARGE_MARKER` (Section 20.5: same phrase in both viewers).
const String diffTooLargeMarker = 'diff too large';

enum PatchLineKind { context, add, del }

/// One rendered diff line with both-side line numbers (null = absent).
class PatchLine {
  const PatchLine({
    required this.kind,
    required this.content,
    required this.oldLine,
    required this.newLine,
    this.noNewline = false,
  });

  final PatchLineKind kind;

  /// Line content without the +/-/space prefix.
  final String content;
  final int? oldLine;
  final int? newLine;

  /// Set when a `\ No newline at end of file` marker follows this line.
  final bool noNewline;
}

/// One `@@ -a,b +c,d @@` hunk with its body lines.
class PatchHunk {
  const PatchHunk({
    required this.header,
    required this.oldStart,
    required this.oldLines,
    required this.newStart,
    required this.newLines,
    required this.lines,
  });

  final String header;
  final int oldStart;
  final int oldLines;
  final int newStart;
  final int newLines;
  final List<PatchLine> lines;
}

enum PatchFileStatus { modified, added, deleted, renamed, binary }

/// One changed file section: identity, status and parsed content.
class PatchFile {
  PatchFile(
      {required this.path,
      this.oldPath,
      this.status = PatchFileStatus.modified});

  /// New-side repo-relative path (the rename target; the only side for
  /// deletes).
  String path;

  /// Old-side path for renames; null otherwise.
  String? oldPath;
  PatchFileStatus status;
  bool isBinary = false;
  final List<PatchHunk> hunks = <PatchHunk>[];

  /// In-section lines no rule understood (combined diffs, submodules) —
  /// rendered as text.
  final List<String> opaque = <String>[];

  /// Total hunk-body lines — structure for the per-file cap, not stats.
  int get lineCount =>
      hunks.fold<int>(0, (int sum, PatchHunk h) => sum + h.lines.length);
}

/// The parse of one patch body: files in first-seen order + opaque
/// preamble.
class ParsedPatch {
  const ParsedPatch({required this.files, required this.opaque});

  final List<PatchFile> files;

  /// Lines before the first file header that no rule understood.
  final List<String> opaque;
}

/// Outcome of interpreting one `GET /resolutions/{id}/patch` payload
/// (Section 9.7's both paths).
sealed class PatchPayloadResult {
  const PatchPayloadResult();
}

class ParsedPatchResult extends PatchPayloadResult {
  const ParsedPatchResult(this.patch);
  final ParsedPatch patch;
}

/// Stats/file-list only — the marker phrase Section 9.7 fixes for the
/// viewers.
class NoBodyPatchResult extends PatchPayloadResult {
  const NoBodyPatchResult(this.marker);
  final String marker;
}

final RegExp _gitHeader = RegExp(
  r'^diff --git (?:"a/([^"]+)"|a/(\S+)) (?:"b/([^"]+)"|b/(\S+))$',
);
final RegExp _hunkHeader =
    RegExp(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@');
final RegExp _binaryLine = RegExp(r'^Binary files (\S+) and (\S+) differ$');
final RegExp _renameFrom = RegExp(r'^rename from (.+)$');
final RegExp _renameTo = RegExp(r'^rename to (.+)$');

/// Git metadata lines inside a section that carry no renderable content.
const List<String> _metadataPrefixes = <String>[
  'index ',
  'old mode ',
  'new mode ',
  'new file mode ',
  'deleted file mode ',
  'similarity index ',
  'dissimilarity index ',
  'GIT binary patch',
];

/// `a/x` / `b/x` / tab-timestamp / `/dev/null` → a repo path or null.
String? _stripSide(String raw) {
  String path = raw.trim();
  final int tab = path.indexOf('\t'); // diff -u appends "\t<ctime>"
  if (tab >= 0) {
    path = path.substring(0, tab).trim();
  }
  if (path.length >= 2 && path.startsWith('"') && path.endsWith('"')) {
    path = path.substring(1, path.length - 1).replaceAll(r'\"', '"');
  }
  if (path == '/dev/null') {
    return null;
  }
  if (path.startsWith('a/') || path.startsWith('b/')) {
    path = path.substring(2);
  }
  return path.isEmpty ? null : path;
}

/// `@@ -a,b +c,d @@` counts — an omitted count reads as 1 (unified-diff
/// default).
int _hunkCount(String? value) => value == null ? 1 : int.parse(value);

/// Parse one unified patch into files/hunks/lines. An empty input is a
/// legitimate "no changes" patch, not an error.
ParsedPatch parseUnifiedPatch(String text) {
  // CRLF and lone \r both normalize here (RISK-15).
  final List<String> lines = text
      .split('\n')
      .map((String line) =>
          line.endsWith('\r') ? line.substring(0, line.length - 1) : line)
      .toList();
  final bool hasGitHeaders =
      lines.any((String line) => line.startsWith('diff --git '));

  final List<PatchFile> files = <PatchFile>[];
  final Map<String, PatchFile> byPath = <String, PatchFile>{};
  final List<String> opaque = <String>[];

  PatchFile? current;
  String? headerPath; // b-side of the open git section
  PatchHunk? currentHunk;
  int oldRemaining = 0; // hunk-body lines left on each side (0 = outside)
  int newRemaining = 0;

  void closeHunk() {
    // Only ends the "last opened hunk" pointer (a new section starts);
    // hunk-body counts are consumed naturally and are always 0 in the
    // guarded branches — mirroring the web parser exactly.
    currentHunk = null;
  }

  /// The open hunk's own lines list — every push goes into the hunk
  /// object directly so a later hunk never clobbers an earlier one.
  List<PatchLine> hunkLines() => currentHunk!.lines;

  PatchFile openFile(String path, String? oldPath) {
    final PatchFile? existing = byPath[path];
    if (existing != null) {
      return existing; // one entry per path, mirroring the server's dedupe
    }
    final PatchFile file = PatchFile(path: path, oldPath: oldPath);
    byPath[path] = file;
    files.add(file);
    return file;
  }

  bool isMetadata(String line) => _metadataPrefixes.any(line.startsWith);

  int index = 0;
  while (index < lines.length) {
    final String line = lines[index];
    final bool inHunk = oldRemaining > 0 || newRemaining > 0;

    if (!inHunk && hasGitHeaders) {
      final RegExpMatch? git = _gitHeader.firstMatch(line);
      if (git != null) {
        closeHunk();
        headerPath = _stripSide(git.group(3) ?? git.group(4) ?? '');
        current = headerPath != null ? openFile(headerPath, null) : null;
        index += 1;
        continue;
      }
    }

    if (!inHunk) {
      final RegExpMatch? from = _renameFrom.firstMatch(line);
      if (from != null) {
        current?.oldPath = _stripSide(from.group(1)!);
        index += 1;
        continue;
      }
      final RegExpMatch? to = _renameTo.firstMatch(line);
      if (to != null) {
        final String? newPath = _stripSide(to.group(1)!);
        final PatchFile? open = current;
        if (open != null && newPath != null && open.path != newPath) {
          byPath.remove(open.path); // re-key under the rename target
          open.path = newPath;
          byPath[newPath] = open;
        }
        open?.status = PatchFileStatus.renamed;
        index += 1;
        continue;
      }
      if (line.startsWith('new file mode ') &&
          current != null &&
          current.status == PatchFileStatus.modified) {
        current.status = PatchFileStatus.added;
        index += 1;
        continue;
      }
      if (line.startsWith('deleted file mode ') &&
          current != null &&
          current.status == PatchFileStatus.modified) {
        current.status = PatchFileStatus.deleted;
        index += 1;
        continue;
      }
    }

    // ---/+++ pair: a file header only outside a hunk and only when both
    // consecutive lines agree — the server's reading, mirrored.
    if (!inHunk && line.startsWith('--- ') && index + 1 < lines.length) {
      final String following = lines[index + 1];
      if (following.startsWith('+++ ')) {
        final String? oldSide = _stripSide(line.substring(4));
        final String? newSide = _stripSide(following.substring(4));
        final String? path = newSide ?? oldSide ?? headerPath;
        if (path != null) {
          current = openFile(path, oldSide);
          closeHunk();
          if (oldSide == null) {
            current.status = PatchFileStatus.added;
          } else if (newSide == null) {
            current.status = PatchFileStatus.deleted;
          } else if (oldSide != newSide) {
            current.status = PatchFileStatus.renamed;
          }
        }
        index += 2;
        continue;
      }
    }

    if (!inHunk) {
      final RegExpMatch? binary = _binaryLine.firstMatch(line);
      if (binary != null) {
        final String? path = _stripSide(binary.group(2)!) ??
            _stripSide(binary.group(1)!) ??
            headerPath;
        if (path != null) {
          current = openFile(path, null);
          current.isBinary = true;
          current.status = PatchFileStatus.binary;
          closeHunk();
        }
        index += 1;
        continue;
      }
    }

    if (!inHunk) {
      final RegExpMatch? hunkMatch = _hunkHeader.firstMatch(line);
      if (hunkMatch != null) {
        PatchFile? target =
            current ?? (headerPath != null ? openFile(headerPath, null) : null);
        if (target != null) {
          final int oldLines = _hunkCount(hunkMatch.group(2));
          final int newLines = _hunkCount(hunkMatch.group(4));
          currentHunk = PatchHunk(
            header: line,
            oldStart: int.parse(hunkMatch.group(1)!),
            oldLines: oldLines,
            newStart: int.parse(hunkMatch.group(3)!),
            newLines: newLines,
            lines: <PatchLine>[],
          );
          target.hunks.add(currentHunk!);
          oldRemaining = oldLines;
          newRemaining = newLines;
        }
        index += 1;
        continue;
      }
    }

    // "\ No newline at end of file" annotates the previous content line
    // and never consumes a count — it must not fall through to opaque.
    if (currentHunk != null && line.startsWith(r'\')) {
      final List<PatchLine> lines0 = hunkLines();
      if (lines0.isNotEmpty) {
        final PatchLine last = lines0.removeLast();
        lines0.add(PatchLine(
          kind: last.kind,
          content: last.content,
          oldLine: last.oldLine,
          newLine: last.newLine,
          noNewline: true,
        ));
      }
      index += 1;
      continue;
    }

    if (inHunk && currentHunk != null) {
      final PatchHunk hunk = currentHunk!;
      final List<PatchLine> lines0 = hunkLines();
      if (line.startsWith('+')) {
        final int newLine = hunk.newStart + (hunk.newLines - newRemaining);
        lines0.add(PatchLine(
          kind: PatchLineKind.add,
          content: line.substring(1),
          oldLine: null,
          newLine: newLine,
        ));
        newRemaining -= 1;
      } else if (line.startsWith('-')) {
        final int oldLine = hunk.oldStart + (hunk.oldLines - oldRemaining);
        lines0.add(PatchLine(
          kind: PatchLineKind.del,
          content: line.substring(1),
          oldLine: oldLine,
          newLine: null,
        ));
        oldRemaining -= 1;
      } else {
        final int oldLine = hunk.oldStart + (hunk.oldLines - oldRemaining);
        final int newLine = hunk.newStart + (hunk.newLines - newRemaining);
        lines0.add(PatchLine(
          kind: PatchLineKind.context,
          content: line.startsWith(' ') ? line.substring(1) : line,
          oldLine: oldLine,
          newLine: newLine,
        ));
        oldRemaining -= 1;
        newRemaining -= 1;
      }
      index += 1;
      continue;
    }

    // Outside every hunk: header metadata skipped; unknown prose inside
    // a section becomes opaque so unparseable regions still render.
    if (line.trim().isNotEmpty) {
      final PatchFile? open = current;
      if (open != null) {
        if (!isMetadata(line) && !line.startsWith('diff --git ')) {
          open.opaque.add(line);
        }
      } else if (!line.startsWith('diff --git ')) {
        opaque.add(line);
      }
    }
    index += 1;
  }

  return ParsedPatch(files: files, opaque: opaque);
}

/// Interpret one `GET /resolutions/{id}/patch` payload (Section 9.7's
/// both paths). `noBody` triggers only on the server's own
/// representation (`diff_too_large` set, or no `patch` body) — never on
/// a client-side byte-size guess. An empty string body is a legitimate
/// empty diff that parses to zero files.
PatchPayloadResult interpretPatchPayload({
  required bool diffTooLarge,
  required String? patch,
  String? marker,
}) {
  if (diffTooLarge || patch == null) {
    final String trimmed = marker?.trim() ?? '';
    return NoBodyPatchResult(
      trimmed.isEmpty ? diffTooLargeMarker : trimmed,
    );
  }
  return ParsedPatchResult(parseUnifiedPatch(patch));
}
