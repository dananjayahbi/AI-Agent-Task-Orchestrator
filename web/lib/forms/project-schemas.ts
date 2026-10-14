/**
 * Shared form validation schemas (MT-4.2-02; Section 13.3 "forms validated
 * with shared schemas"). One module, reused by every project form — the
 * create and edit flows cannot drift apart, and the bounds mirror the
 * published contract (schemas/openapi.yaml field constraints), never
 * invented limits.
 */

export type FieldErrors = Partial<Record<string, string>>;

const REQUIRED = 'This field is required.';

function checkLength(value: string, max: number): string | null {
  if (value.length > max) {
    return `Keep this to ${max} characters or fewer (currently ${value.length}).`;
  }
  return null;
}

export type ProjectFormValues = {
  name: string;
  repo_path: string;
  default_branch: string;
};

type DraftErrors = Record<string, string | null>;

function prune(errors: DraftErrors): FieldErrors {
  return Object.fromEntries(
    Object.entries(errors).filter((entry): entry is [string, string] => entry[1] !== null),
  );
}

/** Required + maxLength checks shared by create and edit (ProjectCreate /
 * PatchedProjectUpdate constraints). */
export function validateProjectFields(values: ProjectFormValues): FieldErrors {
  const errors: DraftErrors = {};
  errors.name = values.name.trim() === '' ? REQUIRED : checkLength(values.name, 200);
  errors.repo_path = values.repo_path.trim() === '' ? REQUIRED : checkLength(values.repo_path, 500);
  errors.default_branch =
    values.default_branch.trim() === '' ? REQUIRED : checkLength(values.default_branch, 255);
  return prune(errors);
}

export type PolicyFormValues = {
  lease_duration_minutes: string;
  lease_max_total_minutes: string;
  lease_extension_mode: string;
  max_retries: string;
  max_concurrent_tasks: string;
  autonomous_diff_threshold_lines: string;
  auditor_min_confidence: string;
  stalled_after_minutes: string;
  branch_prefix: string;
  /** MT-4.10-03: the three Section 12.3 glob lists, newline-joined. */
  critical_path_globs?: string;
  migration_path_globs?: string;
  sensitive_config_globs?: string;
};

// Section 12.3 / backend apps/projects/services/globs.py mirror
// (MT-4.10-03): the client checks the common rejections for immediate
// feedback; the server's validator remains the authority and its
// VALIDATION_ERROR still maps to the form banner.
const MAX_GLOBS_PER_LIST = 64;
const MAX_GLOB_LENGTH = 500;
const NUL = String.fromCharCode(0);

/** One glob's problems, mirroring `validate_glob_list`'s checks; null = ok. */
export function globProblem(raw: string): string | null {
  const glob = raw.trim();
  if (glob === '') {
    return 'must not be empty';
  }
  if (glob.length > MAX_GLOB_LENGTH) {
    return `must be at most ${MAX_GLOB_LENGTH} characters`;
  }
  if (glob.includes('\\')) {
    return 'must use forward slashes, not backslashes';
  }
  if (glob.includes(NUL)) {
    return 'must not contain NUL';
  }
  if (glob.startsWith('/') || (glob.length >= 2 && /^[a-zA-Z]:/.test(glob))) {
    return 'must be relative to the repo root (not absolute)';
  }
  if (glob.split('/').includes('..')) {
    return "must not traverse outside the repo root ('..')";
  }
  for (const match of glob.matchAll(/\*+/g)) {
    const run = match[0];
    if (run.length >= 2) {
      const start = match.index ?? 0;
      const end = start + run.length;
      const wholeSegment =
        (start === 0 || glob[start - 1] === '/') && (end === glob.length || glob[end] === '/');
      if (!wholeSegment) {
        return "'**' is only allowed as a whole path segment";
      }
    }
  }
  const opens = glob.match(/\[/g)?.length ?? 0;
  const closes = glob.match(/\]/g)?.length ?? 0;
  if (opens !== closes) {
    return 'has an unbalanced "[" character class';
  }
  return null;
}

/** One newline-joined textarea's problems; null = ok. */
export function validateGlobListField(raw: string): string | null {
  const entries = raw.split('\n').filter((line) => line.trim() !== '');
  if (entries.length > MAX_GLOBS_PER_LIST) {
    return `At most ${MAX_GLOBS_PER_LIST} globs.`;
  }
  for (const entry of entries) {
    const problem = globProblem(entry);
    if (problem !== null) {
      return `Invalid glob "${entry.trim()}": ${problem}.`;
    }
  }
  return null;
}

/**
 * Numeric bounds transcribed from the ProjectPolicy contract (minimums,
 * 1–5 confidence, non-empty branch prefix); values arrive as input strings
 * so the validator works on exactly what the user sees.
 */
export function validatePolicyFields(values: PolicyFormValues): FieldErrors {
  const errors: DraftErrors = {};
  const positive: Array<[keyof PolicyFormValues, number]> = [
    ['lease_duration_minutes', 1],
    ['lease_max_total_minutes', 1],
    ['max_retries', 1],
    ['autonomous_diff_threshold_lines', 1],
    ['stalled_after_minutes', 1],
  ];
  for (const [field, min] of positive) {
    const parsed = Number(values[field]);
    if (!Number.isInteger(parsed) || parsed < min) {
      errors[field] = `Enter a whole number of ${min} or more.`;
    }
  }
  const concurrent = Number(values.max_concurrent_tasks);
  if (!Number.isInteger(concurrent) || concurrent < 0) {
    errors.max_concurrent_tasks = 'Enter a whole number of 0 or more.';
  }
  const confidence = Number(values.auditor_min_confidence);
  if (!Number.isInteger(confidence) || confidence < 1 || confidence > 5) {
    errors.auditor_min_confidence = 'Enter a confidence between 1 and 5.';
  }
  errors.branch_prefix = values.branch_prefix.trim() === '' ? REQUIRED : null;
  // MT-4.10-03: Section 12.3 glob syntax mirrored for immediate feedback.
  for (const field of [
    'critical_path_globs',
    'migration_path_globs',
    'sensitive_config_globs',
  ] as const) {
    const raw = values[field];
    if (raw !== undefined) {
      errors[field] = validateGlobListField(raw);
    }
  }
  return prune(errors);
}
