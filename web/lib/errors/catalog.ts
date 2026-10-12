/**
 * Canonical error-code → friendly-state mapping (MT-4.1-04; parent plan
 * Section 9.2 catalog × Section 13.3 behaviour). ONE shared source for the
 * whole web app (Section 19.6): every page maps through `resolveError`, never
 * raw server strings or bare codes (G-07).
 *
 * `CANONICAL_ERROR_CODES` mirrors `schemas/openapi.yaml`'s `CodeEnum` in the
 * plan's order — web/tests/errors/catalog.test.ts fails when the published
 * list and this table diverge, so a new backend code cannot ship without a
 * friendly message (Section 20.4 item 5's UI counterpart).
 */

/**
 * Presentation default per code (MT-4.1-04 risk note: Section 13.3 names
 * states, not per-code placements — this matrix is the WP's interpretation,
 * recorded in the changelog; feature WPs may place a message differently
 * without touching the copy):
 *
 * * `redirect` — handled by routing, never rendered (silent sign-in);
 * * `inline`   — attached to the form/field that caused it;
 * * `toast`    — transient operational feedback;
 * * `state`    — full in-page state (blockers, denials, failures).
 */
export type Presentation = 'redirect' | 'inline' | 'toast' | 'state';

export type ErrorEntry = {
  title: string;
  message: string;
  presentation: Presentation;
};

export const CANONICAL_ERROR_CODES = [
  'AUTH_REQUIRED',
  'AUTH_FORBIDDEN_PROJECT',
  'VALIDATION_ERROR',
  'TASK_NOT_FOUND',
  'TASK_STATE_CONFLICT',
  'TASK_ALREADY_CLAIMED',
  'LEASE_EXPIRED',
  'LEASE_NOT_OWNED',
  'DEPENDENCY_UNMET',
  'CONCURRENCY_LIMIT_REACHED',
  'SCOPE_VIOLATION',
  'ROLE_NOT_PERMITTED',
  'AUDITOR_SAME_AS_CODER',
  'ATTACHMENT_NOT_READY',
  'ATTACHMENT_UNSUPPORTED_FORMAT',
  'POLICY_VIOLATION',
  'RATE_LIMITED',
  'VERSION_CONFLICT',
  'SERVER_ERROR',
] as const;

export type ErrorCode = (typeof CANONICAL_ERROR_CODES)[number];

export const ERROR_CATALOG: Record<ErrorCode, ErrorEntry> = {
  AUTH_REQUIRED: {
    title: 'Sign-in required',
    message: 'Sign-in is required. Check your username and password and try again.',
    presentation: 'redirect',
  },
  AUTH_FORBIDDEN_PROJECT: {
    title: "You don't have access",
    message:
      "You don't have access to this project. If you think you should, ask the project owner to grant you access.",
    presentation: 'state',
  },
  VALIDATION_ERROR: {
    title: 'Check your entries',
    message: "Some of the information you provided isn't valid. Review the fields and try again.",
    presentation: 'inline',
  },
  TASK_NOT_FOUND: {
    title: 'Task not found',
    message: 'This task does not exist or has been removed.',
    presentation: 'state',
  },
  TASK_STATE_CONFLICT: {
    title: 'Task changed',
    message: 'This task changed since you loaded it. Refresh the page and try again.',
    presentation: 'toast',
  },
  TASK_ALREADY_CLAIMED: {
    title: 'Already claimed',
    message: 'Another worker is already working on this task. Pick a different task.',
    presentation: 'toast',
  },
  LEASE_EXPIRED: {
    title: 'Claim expired',
    message:
      'Your claim on this task expired before the work was submitted. Claim the task again to continue.',
    presentation: 'toast',
  },
  LEASE_NOT_OWNED: {
    title: 'Not your task',
    message: 'You can only submit work for a task you currently hold a claim on.',
    presentation: 'toast',
  },
  DEPENDENCY_UNMET: {
    title: 'Dependencies not ready',
    message: "This task can't start until its dependencies are complete.",
    presentation: 'toast',
  },
  CONCURRENCY_LIMIT_REACHED: {
    title: 'At capacity',
    message: 'The concurrency limit has been reached. Wait for a slot to free up, then try again.',
    presentation: 'toast',
  },
  SCOPE_VIOLATION: {
    title: 'Outside the allowed scope',
    message:
      "The change touches files outside this task's allowed scope. Narrow the change or update the task's target scope.",
    presentation: 'state',
  },
  ROLE_NOT_PERMITTED: {
    title: 'Not allowed',
    message:
      "Your role doesn't allow this action. If you need it, ask the workspace owner to grant access.",
    presentation: 'state',
  },
  AUDITOR_SAME_AS_CODER: {
    title: 'Independent audit required',
    message: 'The auditor must be different from the coder. Reassign this audit to someone else.',
    presentation: 'inline',
  },
  ATTACHMENT_NOT_READY: {
    title: 'Attachment not ready',
    message: 'This attachment is still being processed. Wait for it to finish, then try again.',
    presentation: 'inline',
  },
  ATTACHMENT_UNSUPPORTED_FORMAT: {
    title: 'Unsupported file',
    message: "That file type isn't supported. Upload one of the accepted formats instead.",
    presentation: 'inline',
  },
  POLICY_VIOLATION: {
    title: 'Blocked by policy',
    message:
      "This action violates the project's policy. Review the policy, adjust the action, or ask the project owner.",
    presentation: 'state',
  },
  RATE_LIMITED: {
    title: 'Slow down',
    message: 'Too many requests. Wait a moment and try again.',
    presentation: 'toast',
  },
  VERSION_CONFLICT: {
    title: 'Outdated version',
    message: 'Someone else updated this first. Reload to get the latest version, then retry.',
    presentation: 'toast',
  },
  SERVER_ERROR: {
    title: 'Something went wrong',
    message:
      'The server had a problem handling this request. Try again — if it keeps failing, share the reference ID with support.',
    presentation: 'state',
  },
};

/** Unknown/uncatalogued codes degrade to this (Section 13.3; G-07). */
export const GENERIC_ERROR: ErrorEntry = {
  title: 'Something went wrong',
  message: "We couldn't complete that request. Please try again.",
  presentation: 'state',
};

export function isErrorCode(code: string): code is ErrorCode {
  return (CANONICAL_ERROR_CODES as readonly string[]).includes(code);
}
