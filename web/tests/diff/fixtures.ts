/**
 * WP-4.7 diff-viewer fixtures (MT-4.7-01…05): sample unified patches
 * covering every format reading the parser mirrors from the backend
 * (git sections, renames, new/delete, binary, no-newline, CRLF,
 * empty), a 5,000-line performance fixture (Wave 9 exit), and the
 * Section 9.7 payload shapes (body path + stats-only oversize path).
 *
 * The small fixtures deliberately mirror the backend parser's sample
 * artifacts (`backend/apps/tasks/services/patch_parse.py` docstring +
 * its tests) so the two parsers' readings are asserted against the
 * same documents — the duplication the MT risk note accepts, never a
 * client-side re-derivation of stats.
 */
import type { ResolutionPatch } from '@/lib/api/generated/types.gen';

/** One minimal single-file git-format patch (one context, one del, one add). */
export const SINGLE_FILE_PATCH = [
  'diff --git a/web/login.tsx b/web/login.tsx',
  'index 1111111..2222222 100644',
  '--- a/web/login.tsx',
  '+++ b/web/login.tsx',
  '@@ -1,3 +1,3 @@',
  ' export function Login() {',
  '-  return <form />;',
  '+  return <form onSubmit={handleSubmit} />;',
  ' }',
  '',
].join('\n');

/** Two files, one of them a rename — b-side path counts once. */
export const MULTI_FILE_RENAME_PATCH = [
  'diff --git a/src/old_name.py b/src/new_name.py',
  'similarity index 92%',
  'rename from src/old_name.py',
  'rename to src/new_name.py',
  'index aaaaaaa..bbbbbbb 100644',
  '--- a/src/old_name.py',
  '+++ b/src/new_name.py',
  '@@ -1,2 +1,2 @@',
  ' import os',
  '-print(os.getcwd())',
  '+print(os.path.abspath("."))',
  'diff --git a/docs/readme.md b/docs/readme.md',
  'index ccccccc..ddddddd 100644',
  '--- a/docs/readme.md',
  '+++ b/docs/readme.md',
  '@@ -1,1 +1,2 @@',
  ' # Docs',
  '+More docs.',
  '',
].join('\n');

/** A new file (from /dev/null). */
export const NEW_FILE_PATCH = [
  'diff --git a/backend/new_module.py b/backend/new_module.py',
  'new file mode 100644',
  'index 0000000..eeeeeee',
  '--- /dev/null',
  '+++ b/backend/new_module.py',
  '@@ -0,0 +1,2 @@',
  '+def helper():',
  '+    return 42',
  '',
].join('\n');

/** A deleted file (to /dev/null). */
export const DELETED_FILE_PATCH = [
  'diff --git a/legacy/old.py b/legacy/old.py',
  'deleted file mode 100644',
  'index fffffff..0000000',
  '--- a/legacy/old.py',
  '+++ /dev/null',
  '@@ -1,2 +0,0 @@',
  '-def legacy():',
  '-    pass',
  '',
].join('\n');

/** A binary file entry (no hunks; nothing invented). */
export const BINARY_PATCH = [
  'diff --git a/assets/logo.png b/assets/logo.png',
  'index 1234567..89abcde 100644',
  'Binary files a/assets/logo.png and b/assets/logo.png differ',
  '',
].join('\n');

/** A hunk with the `\ No newline at end of file` marker on both sides. */
export const NO_NEWLINE_PATCH = [
  'diff --git a/config.toml b/config.toml',
  '--- a/config.toml',
  '+++ b/config.toml',
  '@@ -1,2 +1,2 @@',
  ' [section]',
  '-key = "old"',
  '\\ No newline at end of file',
  '+key = "new"',
  '\\ No newline at end of file',
  '',
].join('\n');

/** CRLF line endings throughout (RISK-15). */
export const CRLF_PATCH = SINGLE_FILE_PATCH.replace(/\n/g, '\r\n');

/** A plain unified diff (no `diff --git` headers; diff -u style). */
export const PLAIN_UNIFIED_PATCH = [
  '--- scripts/build.sh\t2026-10-01 09:00:00',
  '+++ scripts/build.sh\t2026-10-01 10:00:00',
  '@@ -1,2 +1,2 @@',
  ' echo building',
  '-rm -rf dist',
  '+rm -rf build',
  '',
].join('\n');

/** A hunk-body deletion that looks like a file header (`-- …` content). */
export const TRICKY_DASH_PATCH = [
  'diff --git a/notes.md b/notes.md',
  '--- a/notes.md',
  '+++ b/notes.md',
  '@@ -1,4 +1,2 @@',
  ' intro',
  '--- this is hunk-body content, not a file header',
  '-removed line',
  ' tail',
  '',
].join('\n');

/**
 * A 5,000-line performance fixture (Wave 9 exit): one file, one big
 * hunk — `bodyLines` content lines between the hunk header and the
 * final newline.
 */
export function makeLargePatch(bodyLines = 5000): string {
  const body: string[] = [];
  let deletions = 0;
  let additions = 0;
  for (let index = 0; index < bodyLines; index += 1) {
    // Mostly context with scattered edits — a realistic mix.
    if (index % 50 === 0) {
      body.push(`-const removed${index} = ${index};`);
      deletions += 1;
    } else if (index % 25 === 0) {
      body.push(`+const added${index} = ${index};`);
      additions += 1;
    } else {
      body.push(` export const value${index} = ${index};`);
    }
  }
  const lines = [
    'diff --git a/generated/big.ts b/generated/big.ts',
    'index 1111111..2222222 100644',
    '--- a/generated/big.ts',
    '+++ b/generated/big.ts',
    `@@ -1,${bodyLines - additions} +1,${bodyLines - deletions} @@`,
    ...body,
    '',
  ];
  return lines.join('\n');
}

/** Section 9.7 body path: a served patch with `diff_too_large` false. */
export function patchBodyPayload(patch: string): ResolutionPatch {
  return {
    resolution_id: 'res-0002',
    kind: 'patch',
    sha256: '0'.repeat(64),
    size_bytes: patch.length,
    diff_too_large: false,
    patch,
    marker: null,
  };
}

/** Section 9.7 oversize path: stats + file list only, marker phrase. */
export function oversizePatchPayload(): ResolutionPatch {
  return {
    resolution_id: 'res-0002',
    kind: 'patch',
    sha256: 'f'.repeat(64),
    size_bytes: 6_000_000, // over the 5 MB default cap
    diff_too_large: true,
    patch: null,
    marker: 'diff too large',
  };
}

/** The Section 9.4 persisted rule-result row shape (WP-3.4). */
export function ruleRow(
  rule: string,
  passed: boolean,
  reviewReason: string | null = null,
  files?: string[],
): Record<string, unknown> {
  const row: Record<string, unknown> = { rule, passed, review_reason: reviewReason };
  if (files !== undefined) row['files'] = files;
  return row;
}
