/**
 * Shared task-form validation (MT-4.5-01; Section 13.3 "forms validated
 * with shared schemas"; mirrors the WP-1.4 field contract).
 *
 * The bounds transcribe the published contract
 * (`schemas/openapi.yaml` `TaskCreate`/`PatchedTaskUpdate` and the DRF
 * serializers behind them): title required and capped at 200, test
 * command capped at 500, priority one of the four FR-TSK-05 values.
 * Server validation stays the gate (Section 13.3 posture) — this module
 * gives instant client feedback with identical rules so the two cannot
 * drift apart on the happy path.
 */
import type { Task } from '@/lib/api/generated/types.gen';

export const TASK_TITLE_MAX = 200;
export const TEST_COMMAND_MAX = 500;

export const TASK_PRIORITIES = ['urgent', 'high', 'medium', 'low'] as const;

const REQUIRED = 'A title is required.';
const TOO_LONG = (max: number, current: number) =>
  `Keep this to ${max} characters or fewer (currently ${current}).`;

/** Everything the modal edits (Section 13.2 field set minus attachments). */
export type TaskFormValues = {
  title: string;
  /** Markdown, saved byte-identical (MT-4.5-02 round-trip guarantee). */
  description: string;
  acceptance_criteria: string[];
  target_scope: string[];
  test_command: string;
  priority: (typeof TASK_PRIORITIES)[number];
  depends_on: string[];
};

export type TaskFormField =
  | 'title'
  | 'description'
  | 'acceptance_criteria'
  | 'target_scope'
  | 'test_command'
  | 'priority'
  | 'depends_on';

export type TaskFieldErrors = Partial<Record<TaskFormField, string>>;

export function emptyTaskFormValues(): TaskFormValues {
  return {
    title: '',
    description: '',
    acceptance_criteria: [],
    target_scope: [],
    test_command: '',
    priority: 'medium', // documented server default — never invented scope
    depends_on: [],
  };
}

/** Load current server values into the same shape (edit round trip). */
export function taskFormValuesOf(task: Task): TaskFormValues {
  return {
    title: task.title,
    description: task.description,
    acceptance_criteria: [...task.acceptance_criteria],
    target_scope: [...task.target_scope],
    test_command: task.test_command,
    priority: task.priority,
    depends_on: [...task.depends_on],
  };
}

/**
 * Core field validation (MT-4.5-01 scope): title, test command, priority.
 * Criteria/scope add their own rules in `glob-rules.ts` (MT-4.5-03).
 */
export function validateTaskCoreFields(values: TaskFormValues): TaskFieldErrors {
  const errors: TaskFieldErrors = {};
  if (values.title.trim() === '') {
    errors.title = REQUIRED;
  } else if (values.title.length > TASK_TITLE_MAX) {
    errors.title = TOO_LONG(TASK_TITLE_MAX, values.title.length);
  }
  if (values.test_command.length > TEST_COMMAND_MAX) {
    errors.test_command = TOO_LONG(TEST_COMMAND_MAX, values.test_command.length);
  }
  return errors;
}

/**
 * Friendly copy for a server-rejected *field* (Section 13.3). The
 * envelope's raw detail text is never rendered (G-07) — the presence of a
 * field key in `VALIDATION_ERROR` details is enough to attach this
 * generic guidance to that field.
 */
export const SERVER_REJECTED_FIELD = 'The server rejected this value. Review it and try again.';

const KNOWN_FIELDS: readonly TaskFormField[] = [
  'title',
  'description',
  'acceptance_criteria',
  'target_scope',
  'test_command',
  'priority',
  'depends_on',
];

/**
 * Map a `VALIDATION_ERROR` envelope's `details` object onto field-level
 * errors. The backend sends DRF-shaped detail dicts (`{field: ...}` keyed
 * by input name, per-index maps for lists) — any recognized field key
 * gets the friendly rejection message; unknown keys are ignored so a new
 * server detail can never crash the form.
 */
export function fieldErrorsFromDetails(details: unknown): TaskFieldErrors {
  const errors: TaskFieldErrors = {};
  if (typeof details !== 'object' || details === null) {
    return errors;
  }
  for (const field of KNOWN_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(details, field)) {
      errors[field] = SERVER_REJECTED_FIELD;
    }
  }
  return errors;
}

export type ListFieldIndexErrors = Record<number, string>;

/**
 * Map one *list* field's `VALIDATION_ERROR` details (the backend's
 * per-index `{field: {index: [...]}}` shape) onto friendly per-index
 * messages (MT-4.5-03). Unrecognized shapes degrade to no index errors —
 * the field-level message from `fieldErrorsFromDetails` still lands, so a
 * new server detail shape can never crash the form.
 */
export function listFieldErrorsFromDetails(
  details: unknown,
  field: TaskFormField,
): ListFieldIndexErrors {
  const errors: ListFieldIndexErrors = {};
  if (typeof details !== 'object' || details === null) {
    return errors;
  }
  const perField = (details as Record<string, unknown>)[field];
  if (typeof perField !== 'object' || perField === null) {
    return errors;
  }
  for (const key of Object.keys(perField)) {
    const index = Number(key);
    if (Number.isInteger(index) && index >= 0) {
      errors[index] = SERVER_REJECTED_FIELD;
    }
  }
  return errors;
}
