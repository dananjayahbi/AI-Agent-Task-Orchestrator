/**
 * MT-4.7-01 — the client-side unified patch parser: every documented
 * format reading (git sections, ---/+++ pairs, rename, new, delete,
 * binary, no-newline marker, CRLF, plain unified, tricky `--` body
 * content, empty patch), the explicit Section 9.7 oversize/no-body
 * result, the no-statistics discipline (Section 9.7 authority rule;
 * Section 20.5), and the 5,000-line parse budget (Wave 9 exit).
 */
import { describe, expect, it } from 'vitest';

import {
  DIFF_TOO_LARGE_MARKER,
  interpretPatchPayload,
  parseUnifiedPatch,
  fileLineCount,
} from '@/lib/diff/parse';
import {
  BINARY_PATCH,
  CRLF_PATCH,
  DELETED_FILE_PATCH,
  MULTI_FILE_RENAME_PATCH,
  NEW_FILE_PATCH,
  NO_NEWLINE_PATCH,
  PLAIN_UNIFIED_PATCH,
  SINGLE_FILE_PATCH,
  TRICKY_DASH_PATCH,
  makeLargePatch,
  oversizePatchPayload,
  patchBodyPayload,
} from './fixtures';

describe('parseUnifiedPatch (MT-4.7-01)', () => {
  it('parses a single-file git-format patch into files/hunks/lines', () => {
    const patch = parseUnifiedPatch(SINGLE_FILE_PATCH);
    expect(patch.files).toHaveLength(1);
    const file = patch.files[0];
    expect(file?.path).toBe('web/login.tsx');
    expect(file?.status).toBe('modified');
    expect(file?.oldPath).toBeNull();
    expect(file?.hunks).toHaveLength(1);
    const hunk = file?.hunks[0];
    expect(hunk?.header).toBe('@@ -1,3 +1,3 @@');
    expect(hunk?.lines.map((line) => line.kind)).toEqual(['context', 'del', 'add', 'context']);
    // Line numbers track both sides.
    expect(hunk?.lines.map((line) => [line.oldLine, line.newLine])).toEqual([
      [1, 1],
      [2, null],
      [null, 2],
      [3, 3],
    ]);
    expect(hunk?.lines[2]?.content).toBe('  return <form onSubmit={handleSubmit} />;');
  });

  it('parses multiple sections; a rename counts once under the new path', () => {
    const patch = parseUnifiedPatch(MULTI_FILE_RENAME_PATCH);
    expect(patch.files.map((file) => file.path)).toEqual(['src/new_name.py', 'docs/readme.md']);
    const renamed = patch.files[0];
    expect(renamed?.status).toBe('renamed');
    expect(renamed?.oldPath).toBe('src/old_name.py');
    expect(patch.files[1]?.hunks[0]?.lines).toHaveLength(2);
  });

  it('parses a new file (from /dev/null)', () => {
    const patch = parseUnifiedPatch(NEW_FILE_PATCH);
    expect(patch.files).toHaveLength(1);
    expect(patch.files[0]?.status).toBe('added');
    expect(patch.files[0]?.path).toBe('backend/new_module.py');
    const hunk = patch.files[0]?.hunks[0];
    expect(hunk?.lines.every((line) => line.kind === 'add')).toBe(true);
    expect(hunk?.lines.map((line) => line.newLine)).toEqual([1, 2]);
  });

  it('parses a deleted file (to /dev/null)', () => {
    const patch = parseUnifiedPatch(DELETED_FILE_PATCH);
    expect(patch.files).toHaveLength(1);
    expect(patch.files[0]?.status).toBe('deleted');
    expect(patch.files[0]?.hunks[0]?.lines.every((line) => line.kind === 'del')).toBe(true);
  });

  it('parses a binary entry with no hunks and invents nothing', () => {
    const patch = parseUnifiedPatch(BINARY_PATCH);
    expect(patch.files).toHaveLength(1);
    expect(patch.files[0]?.isBinary).toBe(true);
    expect(patch.files[0]?.status).toBe('binary');
    expect(patch.files[0]?.hunks).toEqual([]);
  });

  it('attaches the no-newline marker to the line it follows', () => {
    const patch = parseUnifiedPatch(NO_NEWLINE_PATCH);
    const lines = patch.files[0]?.hunks[0]?.lines ?? [];
    expect(lines.find((line) => line.kind === 'del')?.noNewline).toBe(true);
    expect(lines.find((line) => line.kind === 'add')?.noNewline).toBe(true);
    expect(lines.find((line) => line.kind === 'context')?.noNewline).toBe(false);
  });

  it('parses CRLF content correctly (RISK-15)', () => {
    const crlf = parseUnifiedPatch(CRLF_PATCH);
    const plain = parseUnifiedPatch(SINGLE_FILE_PATCH);
    expect(crlf.files.map((file) => file.path)).toEqual(plain.files.map((file) => file.path));
    const crlfLines = crlf.files[0]?.hunks[0]?.lines ?? [];
    const plainLines = plain.files[0]?.hunks[0]?.lines ?? [];
    expect(crlfLines.map((line) => line.content)).toEqual(plainLines.map((line) => line.content));
    expect(crlfLines.every((line) => !line.content.includes('\r'))).toBe(true);
  });

  it('parses a plain unified diff (no git headers; tab-timestamp stripped)', () => {
    const patch = parseUnifiedPatch(PLAIN_UNIFIED_PATCH);
    expect(patch.files).toHaveLength(1);
    expect(patch.files[0]?.path).toBe('scripts/build.sh');
    expect(patch.files[0]?.hunks[0]?.lines.map((line) => line.kind)).toEqual([
      'context',
      'del',
      'add',
    ]);
  });

  it('treats a hunk-body `-- …` deletion as content, never a file header', () => {
    const patch = parseUnifiedPatch(TRICKY_DASH_PATCH);
    expect(patch.files).toHaveLength(1);
    const lines = patch.files[0]?.hunks[0]?.lines ?? [];
    expect(lines.map((line) => line.kind)).toEqual(['context', 'del', 'del', 'context']);
    expect(lines[1]?.content).toBe('-- this is hunk-body content, not a file header');
  });

  it('handles an empty patch without errors', () => {
    const patch = parseUnifiedPatch('');
    expect(patch.files).toEqual([]);
    expect(patch.opaque).toEqual([]);
    const blank = parseUnifiedPatch('\n\n');
    expect(blank.files).toEqual([]);
  });
});

describe('interpretPatchPayload (Section 9.7 both paths)', () => {
  it('parses a served body', () => {
    const result = interpretPatchPayload(patchBodyPayload(SINGLE_FILE_PATCH));
    expect(result.kind).toBe('parsed');
    if (result.kind === 'parsed') expect(result.patch.files).toHaveLength(1);
  });

  it('maps the stats-only oversize payload to an explicit no-body result', () => {
    const result = interpretPatchPayload(oversizePatchPayload());
    expect(result).toEqual({ kind: 'no-body', marker: 'diff too large' });
  });

  it('falls back to the Section 9.7 phrase when the marker is missing', () => {
    const result = interpretPatchPayload({ patch: null, diff_too_large: true, marker: null });
    expect(result).toEqual({ kind: 'no-body', marker: DIFF_TOO_LARGE_MARKER });
  });

  it('treats a missing body without the flag as no-body (decode guard), never a crash', () => {
    const result = interpretPatchPayload({ patch: null });
    expect(result.kind).toBe('no-body');
  });

  it('an empty string body is an empty diff, distinguishable from no-body', () => {
    const result = interpretPatchPayload(patchBodyPayload(''));
    expect(result.kind).toBe('parsed');
    if (result.kind === 'parsed') expect(result.patch.files).toEqual([]);
  });
});

describe('no-statistics discipline (Section 9.7 authority rule)', () => {
  it('the parser output carries no stats-shaped keys — figures stay the backend’s', () => {
    const patch = parseUnifiedPatch(makeLargePatch(50));
    const scan = (value: unknown): string[] => {
      if (Array.isArray(value)) return value.flatMap(scan);
      if (typeof value === 'object' && value !== null) {
        return Object.entries(value).flatMap(([key, entry]) => [...scan(entry), key]);
      }
      return [];
    };
    const keys = new Set(scan(patch));
    for (const forbidden of ['insertions', 'deletions', 'files_count', 'stats', 'diff_summary']) {
      expect(keys.has(forbidden), `parser output must not carry "${forbidden}"`).toBe(false);
    }
  });

  it('fileLineCount counts structure for collapse rules only', () => {
    const patch = parseUnifiedPatch(SINGLE_FILE_PATCH);
    const file = patch.files[0];
    expect(file !== undefined).toBe(true);
    if (file !== undefined) expect(fileLineCount(file)).toBe(4);
  });
});

describe('5,000-line parse budget (Wave 9 exit)', () => {
  it('parses a 5,000-line patch within the timing budget', () => {
    const text = makeLargePatch(5000);
    const started = performance.now();
    const patch = parseUnifiedPatch(text);
    const elapsed = performance.now() - started;
    expect(patch.files).toHaveLength(1);
    const file = patch.files[0];
    expect(file?.hunks[0]?.lines).toHaveLength(5000);
    // Generous CI budget — the shape matters: linear, not quadratic.
    expect(elapsed).toBeLessThan(2000);
  });
});
