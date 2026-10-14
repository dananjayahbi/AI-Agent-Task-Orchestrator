'use client';

/**
 * Client-side unified-patch parser (MT-4.7-01; FR-WEB-04; Sections 9.7,
 * 13.2) — the **rendering** data layer for the diff viewer.
 *
 * Deliberately separate from the backend's authoritative parser
 * (`backend/apps/tasks/services/patch_parse.py`, WP-32/MT-3.2-03): that
 * one derives `changed_files`/`diff_summary` from the stored bytes;
 * this one turns the patch text into files → hunks → lines so the
 * viewer can render it. The same documented format readings are
 * mirrored so the two agree on what a section is:
 *
 *  - **Git format wins when present** — the bridge uploads `git diff`
 *    output (Section 9.7), whose `diff --git a/x b/y` header delimits
 *    every file section, including mode-only changes and renames.
 *    Inside a section the `---`/`+++` pair is preferred (handles
 *    spaces and quoting); otherwise the header's b-side names the
 *    file — a rename counts once, under the new path.
 *  - **Plain unified diffs** — sections are `---`/`+++` pairs; the
 *    pair only counts when both consecutive lines arrive together and
 *    only outside a hunk, so a hunk-body deletion of a line starting
 *    with `--` is content, never a file header.
 *  - **Binary files** — recorded as changed with no hunks (no lines
 *    exist to render; nothing is invented).
 *  - **CRLF / encoding** — the input is already a JS string (the
 *    transport decoded it); trailing `\r` is stripped per line
 *    (RISK-15), `\ No newline at end of file` marks the line it
 *    follows, and regions no rule understands (combined diffs,
 *    submodules) degrade to opaque text — never a crash and never an
 *    empty-diff masquerade.
 *
 * **No statistics live here** (Section 9.7 authority rule; Section
 * 20.5 traceability): the parser exposes structure only. Every figure
 * the viewer displays comes from the backend's authoritative
 * `diff_summary` on the Task Resolution — asserted in the tests by
 * scanning this module's output for stats-shaped keys.
 *
 * Oversize artifacts (Section 9.7's degraded path) are represented
 * explicitly at the payload level, not the text level:
 * `interpretPatchPayload` maps a stats-and-file-list-only response to
 * an explicit `no-body` result that MT-4.7-04 turns into the "diff too
 * large" marker. The trigger is the server's own representation only —
 * never a client-side byte-size guess (the cap is server-configurable).
 */

export type PatchLineKind = 'context' | 'add' | 'del';

/** One rendered diff line with both-side line numbers (null = absent). */
export type PatchLine = {
  kind: PatchLineKind;
  /** Line content without the +/-/space prefix. */
  content: string;
  oldLine: number | null;
  newLine: number | null;
  /** Set when a `\ No newline at end of file` marker follows this line. */
  noNewline: boolean;
};

/** One `@@ -a,b +c,d @@` hunk with its body lines. */
export type PatchHunk = {
  header: string;
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  lines: PatchLine[];
};

export type PatchFileStatus = 'modified' | 'added' | 'deleted' | 'renamed' | 'binary';

/** One changed file section: identity, status and parsed content. */
export type PatchFile = {
  /** New-side repo-relative path (the rename target; the only side for deletes). */
  path: string;
  /** Old-side path for renames; null otherwise. */
  oldPath: string | null;
  status: PatchFileStatus;
  isBinary: boolean;
  hunks: PatchHunk[];
  /** In-section lines no rule understood (combined diffs, submodules) — rendered as text. */
  opaque: string[];
};

/** The parse of one patch body: files in first-seen order + opaque preamble. */
export type ParsedPatch = {
  files: PatchFile[];
  /** Lines before the first file header that no rule understood — rendered as text. */
  opaque: string[];
};

/** The `GET /resolutions/{id}/patch` payload fields this module interprets. */
export type PatchPayloadLike = {
  patch: string | null;
  diff_too_large?: boolean | null;
  marker?: string | null;
};

/** The explicit outcome of interpreting one patch payload (Section 9.7 both paths). */
export type PatchPayloadResult =
  | { kind: 'parsed'; patch: ParsedPatch }
  /** Stats/file-list only — the marker phrase Section 9.7 fixes for the viewers. */
  | { kind: 'no-body'; marker: string };

/** Section 9.7's verbatim marker phrase (shared with the mobile viewer, WP-5.8). */
export const DIFF_TOO_LARGE_MARKER = 'diff too large';

const GIT_HEADER = /^diff --git (?:"a\/([^"]+)"|a\/(\S+)) (?:"b\/([^"]+)"|b\/(\S+))$/;
const HUNK_HEADER = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/;
const BINARY_LINE = /^Binary files (\S+) and (\S+) differ$/;
const RENAME_FROM = /^rename from (.+)$/;
const RENAME_TO = /^rename to (.+)$/;

/** Git metadata lines inside a section that carry no renderable content. */
const METADATA_PREFIXES = [
  'index ',
  'old mode ',
  'new mode ',
  'new file mode ',
  'deleted file mode ',
  'similarity index ',
  'dissimilarity index ',
  'GIT binary patch',
];

/** `a/x` / `b/x` / tab-timestamp / `/dev/null` → a repo path or null. */
function stripSide(raw: string): string | null {
  let path = raw.trim();
  const tab = path.indexOf('\t'); // diff -u appends "\t<ctime>"
  if (tab >= 0) path = path.slice(0, tab).trim();
  if (path.startsWith('"') && path.endsWith('"') && path.length >= 2) {
    path = path.slice(1, -1).replace(/\\"/g, '"');
  }
  if (path === '/dev/null') return null;
  if (path.startsWith('a/') || path.startsWith('b/')) path = path.slice(2);
  return path === '' ? null : path;
}

/** `@@ -a,b +c,d @@` counts — an omitted count reads as 1 (unified-diff default). */
function hunkCount(value: string | undefined): number {
  return value === undefined ? 1 : Number.parseInt(value, 10);
}

/**
 * Parse one unified patch into files/hunks/lines. Pure and
 * deterministic (ADR-009); an empty input is a legitimate "no
 * changes" patch, not an error.
 */
export function parseUnifiedPatch(text: string): ParsedPatch {
  // CRLF (RISK-15) and lone \r both normalize here.
  const lines = text.split('\n').map((line) => (line.endsWith('\r') ? line.slice(0, -1) : line));
  const hasGitHeaders = lines.some((line) => line.startsWith('diff --git '));

  const files: PatchFile[] = [];
  const byPath = new Map<string, PatchFile>();
  const opaque: string[] = [];

  let current: PatchFile | null = null;
  let headerPath: string | null = null; // b-side of the open git section
  let currentHunk: PatchHunk | null = null;
  let oldRemaining = 0; // hunk-body lines left on each side (0 = outside a hunk)
  let newRemaining = 0;

  const openFile = (path: string, oldPath: string | null): PatchFile => {
    const existing = byPath.get(path);
    if (existing !== undefined) return existing; // one entry per path, mirroring the server's dedupe
    const file: PatchFile = {
      path,
      oldPath,
      status: 'modified',
      isBinary: false,
      hunks: [],
      opaque: [],
    };
    byPath.set(path, file);
    files.push(file);
    return file;
  };

  const isMetadata = (line: string): boolean => METADATA_PREFIXES.some((p) => line.startsWith(p));

  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    const inHunk = oldRemaining > 0 || newRemaining > 0;

    if (!inHunk && hasGitHeaders) {
      const git = GIT_HEADER.exec(line);
      if (git !== null) {
        currentHunk = null;
        headerPath = stripSide(git[3] ?? git[4] ?? '');
        // The section's file opens under the b-side (the server's
        // recorded path); the ---/+++ pair below may refine identity.
        current = headerPath !== null ? openFile(headerPath, null) : null;
        index += 1;
        continue;
      }
    }

    if (!inHunk) {
      const from = RENAME_FROM.exec(line);
      if (from !== null) {
        if (current !== null) current.oldPath = stripSide(from[1]);
        index += 1;
        continue;
      }
      const to = RENAME_TO.exec(line);
      if (to !== null) {
        const newPath = stripSide(to[1]);
        if (current !== null && newPath !== null && current.path !== newPath) {
          byPath.delete(current.path); // re-key under the rename target
          current.path = newPath;
          byPath.set(newPath, current);
        }
        if (current !== null) current.status = 'renamed';
        index += 1;
        continue;
      }
      if (line.startsWith('new file mode ') && current !== null && current.status === 'modified') {
        current.status = 'added';
        index += 1;
        continue;
      }
      if (
        line.startsWith('deleted file mode ') &&
        current !== null &&
        current.status === 'modified'
      ) {
        current.status = 'deleted';
        index += 1;
        continue;
      }
    }

    // ---/+++ pair: a file header only outside a hunk and only when both
    // consecutive lines agree (lookahead keeps a hunk-body "-- ..." line
    // from being mistaken for one) — the server's reading, mirrored.
    if (!inHunk && line.startsWith('--- ') && index + 1 < lines.length) {
      const following = lines[index + 1];
      if (following.startsWith('+++ ')) {
        const oldSide = stripSide(line.slice(4));
        const newSide = stripSide(following.slice(4));
        const path = newSide ?? oldSide ?? headerPath;
        if (path !== null) {
          current = openFile(path, oldSide);
          currentHunk = null;
          if (oldSide === null) current.status = 'added';
          else if (newSide === null) current.status = 'deleted';
          else if (oldSide !== newSide) current.status = 'renamed';
        }
        index += 2;
        continue;
      }
    }

    if (!inHunk) {
      const binary = BINARY_LINE.exec(line);
      if (binary !== null) {
        const path = stripSide(binary[2]) ?? stripSide(binary[1]) ?? headerPath;
        if (path !== null) {
          current = openFile(path, null);
          current.isBinary = true;
          current.status = 'binary';
          currentHunk = null;
        }
        index += 1;
        continue;
      }
    }

    if (!inHunk) {
      const hunkHeader = HUNK_HEADER.exec(line);
      if (hunkHeader !== null) {
        const target = current ?? (headerPath !== null ? openFile(headerPath, null) : null);
        if (target !== null) {
          const oldLines = hunkCount(hunkHeader[2]);
          const newLines = hunkCount(hunkHeader[4]);
          currentHunk = {
            header: line,
            oldStart: Number.parseInt(hunkHeader[1], 10),
            oldLines,
            newStart: Number.parseInt(hunkHeader[3], 10),
            newLines,
            lines: [],
          };
          target.hunks.push(currentHunk);
          oldRemaining = oldLines;
          newRemaining = newLines;
        }
        index += 1;
        continue;
      }
    }

    // "\ No newline at end of file" annotates the previous content
    // line. Git emits it even after the last counted body line (when
    // both hunk sides are already exhausted), so the check runs
    // before the in-hunk count gate — it never consumes a count, and
    // it must not fall through to the opaque-prose branch.
    if (currentHunk !== null && line.startsWith('\\')) {
      const last = currentHunk.lines[currentHunk.lines.length - 1];
      if (last !== undefined) last.noNewline = true;
      index += 1;
      continue;
    }

    if (inHunk && currentHunk !== null) {
      if (line.startsWith('+')) {
        currentHunk.lines.push({
          kind: 'add',
          content: line.slice(1),
          oldLine: null,
          newLine: currentHunk.newStart + (currentHunk.newLines - newRemaining),
          noNewline: false,
        });
        newRemaining -= 1;
      } else if (line.startsWith('-')) {
        currentHunk.lines.push({
          kind: 'del',
          content: line.slice(1),
          oldLine: currentHunk.oldStart + (currentHunk.oldLines - oldRemaining),
          newLine: null,
          noNewline: false,
        });
        oldRemaining -= 1;
      } else {
        // Context (leading space, or the empty line git emits for "").
        currentHunk.lines.push({
          kind: 'context',
          content: line.startsWith(' ') ? line.slice(1) : line,
          oldLine: currentHunk.oldStart + (currentHunk.oldLines - oldRemaining),
          newLine: currentHunk.newStart + (currentHunk.newLines - newRemaining),
          noNewline: false,
        });
        oldRemaining -= 1;
        newRemaining -= 1;
      }
      index += 1;
      continue;
    }

    // Outside every hunk: header metadata (index/mode/similarity) is
    // skipped; unknown prose inside a section becomes opaque so an
    // unparseable region still renders as text (MT risk note).
    if (line.trim() !== '') {
      if (current !== null) {
        if (!isMetadata(line) && !line.startsWith('diff --git ')) current.opaque.push(line);
      } else if (!line.startsWith('diff --git ')) {
        opaque.push(line);
      }
    }
    index += 1;
  }

  return { files, opaque };
}

/**
 * Interpret one `GET /resolutions/{id}/patch` payload (Section 9.7's
 * both paths). The `no-body` result triggers **only** on the server's
 * own representation (`diff_too_large` set, or no `patch` body) —
 * never on a client-side byte-size guess. An empty string body is a
 * legitimate empty diff and parses to zero files, distinguishable
 * from `no-body`.
 */
export function interpretPatchPayload(payload: PatchPayloadLike): PatchPayloadResult {
  // `diff_too_large` is the server's flag; a non-string body (null on
  // the oversize path, or unusable after a decode anomaly) is the
  // client-side guard — marker, never fabricated content.
  if (payload.diff_too_large === true || typeof payload.patch !== 'string') {
    const marker =
      typeof payload.marker === 'string' && payload.marker.trim() !== ''
        ? payload.marker
        : DIFF_TOO_LARGE_MARKER;
    return { kind: 'no-body', marker };
  }
  return { kind: 'parsed', patch: parseUnifiedPatch(payload.patch) };
}

/** Total hunk-body lines of one file — structure for collapse rules, not stats. */
export function fileLineCount(file: PatchFile): number {
  let total = 0;
  for (const hunk of file.hunks) total += hunk.lines.length;
  return total;
}
