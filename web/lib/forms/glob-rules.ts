/**
 * Target-scope glob + acceptance-criteria rules (MT-4.5-03; parent plan
 * Section 12.3 "target_scope globs are validated on creation"; Section
 * 13.3 shared schemas).
 *
 * The glob rules are a line-for-line mirror of WP-1.4's
 * `backend/apps/tasks/services/tasks.validate_target_scope_globs` — the
 * same helper serves POST and PATCH there, so one client mirror covers
 * both paths and the two dialects cannot drift:
 *
 *   - at most 64 globs per task;
 *   - each glob: non-empty after trim, ≤ 500 characters, forward slashes
 *     only (no backslash), no NUL, repo-root-relative (never absolute —
 *     POSIX `/…` or a Windows drive `X:`), no `..` path segment.
 *
 * Not mirrored: the policy-list validator's `**`-segment/character-class
 * syntax check (`apps.projects.services.globs.validate_glob_list`) —
 * WP-1.4's *task* validator deliberately performs no syntax pass, so a
 * client check here would invent a rule the create endpoint accepts.
 * Server validation stays the gate (Section 13.3 posture); the fixture
 * set in `web/tests/task/criteria-scope-editors.test.tsx` pins the mirror.
 */

export const MAX_TARGET_SCOPE_GLOBS = 64;
export const MAX_GLOB_LENGTH = 500;

export type ScopeEntryErrors = Record<number, string[]>;
export type CriteriaEntryErrors = Record<number, string>;

export type ScopeValidation = {
  errors: ScopeEntryErrors;
  /** List-level message (count cap) — shown once above the editor. */
  listError?: string;
  /** Trimmed entries, in order — exactly what the save payload carries. */
  cleaned: string[];
};

/**
 * Mirror of `validate_target_scope_globs` problem messages, in the
 * app's friendly voice (Section 13.3: canonical rules, human copy).
 */
export function validateTargetScope(globs: readonly string[]): ScopeValidation {
  const errors: ScopeEntryErrors = {};
  const cleaned: string[] = [];
  let listError: string | undefined;

  if (globs.length > MAX_TARGET_SCOPE_GLOBS) {
    listError = `At most ${MAX_TARGET_SCOPE_GLOBS} scope globs — remove ${globs.length - MAX_TARGET_SCOPE_GLOBS} to save.`;
  }

  globs.forEach((raw, index) => {
    const glob = raw.trim();
    const problems: string[] = [];
    if (glob === '') {
      problems.push('Enter a glob or remove this row.');
    }
    if (glob.length > MAX_GLOB_LENGTH) {
      problems.push(`Keep the glob to ${MAX_GLOB_LENGTH} characters or fewer.`);
    }
    if (glob.includes('\\')) {
      problems.push('Use forward slashes (/), not backslashes.');
    }
    if (glob.includes('\u0000')) {
      problems.push('A glob cannot contain a NUL character.');
    }
    const driveAbsolute = glob.length >= 2 && /[a-zA-Z]:/.test(glob.slice(0, 2));
    if (glob.startsWith('/') || driveAbsolute) {
      problems.push('Write the glob relative to the repository root (not an absolute path).');
    }
    if (glob.split('/').includes('..')) {
      problems.push("A '..' segment would escape the repository root.");
    }
    if (problems.length > 0) {
      errors[index] = problems;
    } else {
      cleaned.push(glob);
    }
  });

  return listError === undefined ? { errors, cleaned } : { errors, cleaned, listError };
}

export type CriteriaValidation = {
  errors: CriteriaEntryErrors;
  /** Trimmed, non-empty criteria — exactly what the save payload carries. */
  cleaned: string[];
};

/**
 * Acceptance-criteria entries mirror the backend's `ListField(child=
 * CharField())` stance: the list itself is optional (empty is valid —
 * WP-1.4's T2-required-fields reads only the title), but every entry must
 * be a non-blank string, so blank rows are blocked until filled or removed.
 */
export function validateAcceptanceCriteria(entries: readonly string[]): CriteriaValidation {
  const errors: CriteriaEntryErrors = {};
  const cleaned: string[] = [];
  entries.forEach((raw, index) => {
    const entry = raw.trim();
    if (entry === '') {
      errors[index] = 'Fill in this criterion or remove the row.';
      return;
    }
    cleaned.push(entry);
  });
  return { errors, cleaned };
}
