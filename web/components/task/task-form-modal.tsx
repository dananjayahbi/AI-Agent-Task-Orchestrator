'use client';

/**
 * Task create/edit modal (MT-4.5-01; FR-WEB-03; parent plan Section 13.2
 * "Task modal: title, markdown editor with preview, acceptance criteria
 * list editor, target-scope editor with glob validation, test command,
 * priority, dependencies picker, attachment dropzone with per-file
 * processing status").
 *
 * Composition notes (Section 20.3 — layout, data wiring and states are
 * separate concerns):
 *  - the modal is one controlled surface over `TaskFormValues` (shared
 *    schema module, Section 13.3 "forms validated with shared schemas");
 *  - creation follows T1 (Section 8.2): `POST /projects/{pid}/tasks` lands
 *    in `draft` — publishing is MT-4.5-06 and never implicit here;
 *  - edits save through `PATCH /tasks/{id}` carrying the `version` the
 *    client saw (Section 8.2 version discipline; FR-TSK-06);
 *  - the specialized editors (markdown MT-4.5-02, criteria/scope
 *    MT-4.5-03, dependencies MT-4.5-04) and the uploader (MT-4.5-05)
 *    slot into the scaffold sections below — each section region keeps a
 *    stable `task-form-section-*` testid so the scaffold contract stays
 *    assertable across the sub-slices;
 *  - Radix's Dialog (MT-4.1 UI kit) provides focus trapping, Escape and
 *    focus return; unsaved changes are guarded by an explicit discard
 *    confirmation before close (MT-4.5-01 acceptance).
 */
import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { FieldRow, FormBanner } from '@/components/projects/form-field';
import { AttachmentDropzone } from '@/components/task/attachment-dropzone';
import { CriteriaEditor } from '@/components/task/criteria-editor';
import { DependenciesPicker } from '@/components/task/dependencies-picker';
import { MarkdownEditor } from '@/components/task/markdown-editor';
import { PublishAction } from '@/components/task/publish-action';
import { ScopeEditor } from '@/components/task/scope-editor';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { callApi, createTask, isApiError, partialUpdateTask, type Task } from '@/lib/api';
import { resolveError } from '@/lib/errors';
import { validateAcceptanceCriteria, validateTargetScope } from '@/lib/forms/glob-rules';
import {
  emptyTaskFormValues,
  fieldErrorsFromDetails,
  listFieldErrorsFromDetails,
  TASK_PRIORITIES,
  taskFormValuesOf,
  validateTaskCoreFields,
  type TaskFieldErrors,
  type TaskFormValues,
} from '@/lib/forms/task-schemas';
import { queryKeys } from '@/lib/queries/keys';
import type { PublishTransport } from '@/lib/task/publish-seam';

export type TaskFormModalProps = {
  pid: string;
  /** `null` = create mode (T1); a task row = edit mode. */
  task: Task | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /**
   * Called after a successful create with the server row — the board
   * switches the modal into edit mode so uploads (MT-4.5-05) and publish
   * (MT-4.5-06) have a real task id to work against.
   */
  onSaved?: (task: Task) => void;
  /**
   * MT-4.5-06 seam: publish consumer for `POST /tasks/{id}/transition`
   * (absent from the schema — an OQ); without it the publish action
   * shows an explicit unavailable notice.
   */
  publishTransport?: PublishTransport | undefined;
};

/** One stable snapshot for dirty comparison (arrays value-compared). */
function snapshotOf(values: TaskFormValues): string {
  return JSON.stringify(values);
}

export function TaskFormModal({
  pid,
  task,
  open,
  onOpenChange,
  onSaved,
  publishTransport,
}: TaskFormModalProps) {
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  // Content registers its dirty probe here so close requests (Escape, X,
  // overlay) can prompt before discarding — content mounts only while open.
  const isDirtyRef = useRef<() => boolean>(() => false);
  const registerDirty = useCallback((probe: () => boolean) => {
    isDirtyRef.current = probe;
  }, []);

  const requestClose = useCallback(() => {
    if (isDirtyRef.current()) {
      setConfirmDiscard(true);
      return;
    }
    onOpenChange(false);
  }, [onOpenChange]);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (next) {
          onOpenChange(true);
        } else {
          requestClose();
        }
      }}
    >
      {open && (
        <DialogContent
          data-testid="task-form-modal"
          className="max-h-[90vh] max-w-2xl overflow-y-auto"
        >
          <DialogHeader>
            <DialogTitle>{task === null ? 'New task' : `Edit task ${task.id}`}</DialogTitle>
            <DialogDescription>
              {task === null
                ? 'Creates a draft task (T1) — publish it separately when it is ready.'
                : 'Changes are saved to the task; the server re-validates every field.'}
            </DialogDescription>
          </DialogHeader>

          <TaskFormContent
            pid={pid}
            task={task}
            onSaved={onSaved}
            onClose={() => onOpenChange(false)}
            registerDirty={registerDirty}
            publishTransport={publishTransport}
          />

          {confirmDiscard && (
            <div
              role="alertdialog"
              aria-label="Discard unsaved changes"
              data-testid="task-form-discard-confirm"
              className="rounded-md border border-destructive/40 bg-destructive/10 p-3"
            >
              <p className="text-sm font-medium text-foreground">
                You have unsaved changes. Discard them?
              </p>
              <div className="mt-2 flex gap-2">
                <Button
                  data-testid="task-form-discard-confirm-yes"
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    setConfirmDiscard(false);
                    onOpenChange(false);
                  }}
                >
                  Discard changes
                </Button>
                <Button
                  data-testid="task-form-discard-confirm-cancel"
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmDiscard(false)}
                >
                  Keep editing
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      )}
    </Dialog>
  );
}

type TaskFormContentProps = {
  pid: string;
  task: Task | null;
  onSaved?: ((task: Task) => void) | undefined;
  onClose: () => void;
  registerDirty: (probe: () => boolean) => void;
  publishTransport?: PublishTransport | undefined;
};

function TaskFormContent({
  pid,
  task,
  onSaved,
  onClose,
  registerDirty,
  publishTransport,
}: TaskFormContentProps) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState<TaskFormValues>(() =>
    task === null ? emptyTaskFormValues() : taskFormValuesOf(task),
  );
  const [baseline, setBaseline] = useState<string>(() => snapshotOf(values));
  const [errors, setErrors] = useState<TaskFieldErrors>({});
  // Per-index messages for the two list editors (MT-4.5-03): filled by
  // the client validators on submit and overlaid by server details.
  const [entryErrors, setEntryErrors] = useState<{
    criteria: Record<number, string>;
    scope: Record<number, string[]>;
    scopeList?: string;
  }>({ criteria: {}, scope: {} });
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  // Latest server-known version: the CAS token every save sends (it tracks
  // save responses, not the board-cache prop, so a slow refetch cannot make
  // the next PATCH stale).
  const versionRef = useRef<number | null>(task?.version ?? null);
  const valuesRef = useRef(values);
  useEffect(() => {
    valuesRef.current = values;
  }, [values]);
  const sentSnapshotRef = useRef<string | null>(null);
  // Last board-cache row this content adopted — a *changed* id/version
  // (create→edit swap, post-save refetch, VERSION_CONFLICT refresh) syncs
  // server truth into the form; same-version re-renders never clobber edits.
  const lastSeenRowRef = useRef<{ id: string; version: number } | null>(
    task === null ? null : { id: task.id, version: task.version },
  );

  const dirty = snapshotOf(values) !== baseline;
  useEffect(() => {
    registerDirty(() => dirty);
  }, [dirty, registerDirty]);

  useEffect(() => {
    if (task === null) return;
    const seen = { id: task.id, version: task.version };
    const last = lastSeenRowRef.current;
    if (last !== null && last.id === seen.id && last.version === seen.version) return;
    lastSeenRowRef.current = seen;
    versionRef.current = task.version;
    const next = taskFormValuesOf(task);
    setValues(next);
    setBaseline(snapshotOf(next));
    setErrors({});
    setEntryErrors({ criteria: {}, scope: {} });
  }, [task]);

  const save = useMutation({
    mutationFn: (input: { values: TaskFormValues; version: number | null }) =>
      input.version === null
        ? callApi(createTask({ path: { pid }, body: createBodyOf(input.values) }))
        : callApi(
            partialUpdateTask({
              path: { id: task?.id ?? '' },
              body: { ...patchBodyOf(input.values), version: input.version },
            }),
          ),
    onSuccess: (savedTask) => {
      setFormError(null);
      setErrors({});
      setEntryErrors({ criteria: {}, scope: {} });
      versionRef.current = savedTask.version;
      lastSeenRowRef.current = { id: savedTask.id, version: savedTask.version };
      // Adopt server truth when the user kept typing nothing meanwhile;
      // otherwise keep their edits (the bumped versionRef CASes the next
      // save correctly).
      if (valuesRef.current && sentSnapshotRef.current === snapshotOf(valuesRef.current)) {
        const next = taskFormValuesOf(savedTask);
        setValues(next);
        setBaseline(snapshotOf(next));
        setSaved(true);
      } else {
        setSaved(false);
      }
      sentSnapshotRef.current = null;
      void queryClient.invalidateQueries({ queryKey: queryKeys.boardTasksRoot(pid) });
      if (task === null) {
        onSaved?.(savedTask);
      }
    },
    onError: (error) => {
      sentSnapshotRef.current = null;
      setSaved(false);
      if (isApiError(error) && error.code === 'VALIDATION_ERROR') {
        setFieldErrors(fieldErrorsFromDetails(error.details));
        // Per-index server rejections land on the exact list rows (13.3).
        setEntryErrors((current) => ({
          criteria: {
            ...current.criteria,
            ...listFieldErrorsFromDetails(error.details, 'acceptance_criteria'),
          },
          scope: {
            ...current.scope,
            ...Object.fromEntries(
              Object.entries(listFieldErrorsFromDetails(error.details, 'target_scope')).map(
                ([index, message]) => [index, [message]],
              ),
            ),
          },
          scopeList: current.scopeList,
        }));
      }
      if (isApiError(error) && error.code === 'VERSION_CONFLICT') {
        // Section 8.2: "a stale version returns a conflict and the UI
        // refreshes" — invalidate; the refetched row's new version syncs
        // server truth into the form through the effect above.
        void queryClient.invalidateQueries({ queryKey: queryKeys.boardTasksRoot(pid) });
      }
      setFormError(resolveError(error).message);
    },
  });

  function setFieldErrors(next: TaskFieldErrors) {
    setErrors((current) => ({ ...current, ...next }));
  }

  function setField<K extends keyof TaskFormValues>(key: K, value: TaskFormValues[K]) {
    setSaved(false);
    setValues((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fieldErrors = validateTaskCoreFields(values);
    const criteria = validateAcceptanceCriteria(values.acceptance_criteria);
    const scope = validateTargetScope(values.target_scope);
    // Self-dependency guard (MT-4.5-04): the picker excludes it, the
    // server rejects it — this keeps a hand-edited cache honest too.
    if (task !== null && values.depends_on.includes(task.id)) {
      fieldErrors.depends_on = 'A task cannot depend on itself.';
    }
    setErrors(fieldErrors);
    setEntryErrors({
      criteria: criteria.errors,
      scope: scope.errors,
      scopeList: scope.listError,
    });
    const listInvalid =
      Object.keys(criteria.errors).length > 0 ||
      Object.keys(scope.errors).length > 0 ||
      scope.listError !== undefined;
    if (Object.keys(fieldErrors).length > 0 || listInvalid) {
      setFormError(null);
      return;
    }
    // Save trimmed entries — exactly what the server would store.
    const cleanedValues: TaskFormValues = {
      ...values,
      acceptance_criteria: criteria.cleaned,
      target_scope: scope.cleaned,
    };
    setValues(cleanedValues);
    sentSnapshotRef.current = snapshotOf(cleanedValues);
    save.mutate({ values: cleanedValues, version: task === null ? null : versionRef.current });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="grid gap-4" data-testid="task-form">
      {formError !== null && <FormBanner variant="error">{formError}</FormBanner>}
      {saved && <FormBanner variant="success">Changes saved.</FormBanner>}

      <FieldRow htmlFor="task-title" label="Title" error={errors.title}>
        <Input
          id="task-title"
          name="title"
          required
          value={values.title}
          aria-invalid={errors.title !== undefined}
          onChange={(event) => setField('title', event.target.value)}
        />
      </FieldRow>

      {/* Section 13.2 field: markdown editor with preview (MT-4.5-02). */}
      <section data-testid="task-form-section-description" aria-label="Description">
        <FieldRow
          htmlFor="task-description"
          label="Description (markdown)"
          hint="Markdown; saved exactly as typed. Preview renders links and images inertly."
        >
          <MarkdownEditor
            id="task-description"
            value={values.description}
            error={errors.description}
            onChange={(next) => setField('description', next)}
          />
        </FieldRow>
      </section>

      <FormSection testId="task-form-section-criteria" label="Acceptance criteria">
        <CriteriaEditor
          entries={values.acceptance_criteria}
          errors={entryErrors.criteria}
          onChange={(next) => setField('acceptance_criteria', next)}
        />
      </FormSection>
      <FormSection testId="task-form-section-scope" label="Target scope">
        <ScopeEditor
          entries={values.target_scope}
          errors={entryErrors.scope}
          listError={entryErrors.scopeList}
          onChange={(next) => setField('target_scope', next)}
        />
      </FormSection>

      <FieldRow htmlFor="task-test-command" label="Test command" error={errors.test_command}>
        <Input
          id="task-test-command"
          name="test_command"
          value={values.test_command}
          aria-invalid={errors.test_command !== undefined}
          onChange={(event) => setField('test_command', event.target.value)}
        />
      </FieldRow>

      <FieldRow htmlFor="task-priority" label="Priority">
        <select
          id="task-priority"
          name="priority"
          value={values.priority}
          onChange={(event) =>
            setField('priority', event.target.value as TaskFormValues['priority'])
          }
          className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-base md:text-sm dark:bg-input/30"
        >
          {TASK_PRIORITIES.map((priority) => (
            <option key={priority} value={priority}>
              {priority}
            </option>
          ))}
        </select>
      </FieldRow>

      <FormSection testId="task-form-section-dependencies" label="Dependencies">
        <DependenciesPicker
          pid={pid}
          selfTaskId={task?.id ?? null}
          dependsOn={values.depends_on}
          onChange={(next) => setField('depends_on', next)}
        />
        {errors.depends_on !== undefined && (
          <p role="alert" className="text-xs text-destructive">
            {errors.depends_on}
          </p>
        )}
        <p className="text-xs text-muted-foreground">
          Publish (T2) requires every dependency to be completed; claim (T4) checks the same set.
          Cycles and unknown ids are rejected by the server.
        </p>
      </FormSection>
      <FormSection testId="task-form-section-attachments" label="Attachments">
        <AttachmentDropzone pid={pid} taskId={task?.id ?? null} />
      </FormSection>

      {/* MT-4.5-06: publish appears on the saved draft — T2's guards,
          the readiness gate and the explicit override live here. */}
      {task !== null && task.state === 'draft' && (
        <PublishAction
          pid={pid}
          task={task}
          values={values}
          dirty={dirty}
          transport={publishTransport}
        />
      )}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" data-testid="task-form-submit" disabled={save.isPending}>
          {save.isPending ? 'Saving…' : task === null ? 'Create draft task' : 'Save changes'}
        </Button>
      </DialogFooter>
    </form>
  );
}

/** Labeled section wrapper used by the specialized editors. */
function FormSection({
  testId,
  label,
  children,
}: {
  testId: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <section data-testid={testId} aria-label={label} className="grid gap-2">
      <p className="text-sm font-medium text-foreground">{label}</p>
      {children}
    </section>
  );
}

/** T1 create body — the FR-TSK-02 field set only (server assigns the rest). */
function createBodyOf(values: TaskFormValues) {
  return {
    title: values.title,
    description: values.description,
    acceptance_criteria: values.acceptance_criteria,
    target_scope: values.target_scope,
    test_command: values.test_command,
    priority: values.priority,
    depends_on: values.depends_on,
  };
}

/** PATCH body — the same editable set; `version` is attached by the caller. */
function patchBodyOf(values: TaskFormValues) {
  return createBodyOf(values);
}
