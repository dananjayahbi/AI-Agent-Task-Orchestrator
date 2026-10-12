'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { FieldRow, FormBanner } from '@/components/projects/form-field';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { callApi, partialUpdateProject, type Project } from '@/lib/api';
import { resolveError } from '@/lib/errors';
import { validateProjectFields, type FieldErrors } from '@/lib/forms/project-schemas';
import { queryKeys } from '@/lib/queries/keys';

type FormValues = {
  name: string;
  repo_path: string;
  default_branch: string;
};

function toValues(project: Project): FormValues {
  return {
    name: project.name,
    repo_path: project.repo_path,
    default_branch: project.default_branch,
  };
}

/**
 * Edit form for `PATCH /projects/{pid}` (MT-4.2-02). Only changed fields are
 * sent; the server keeps the rest (partial-update contract).
 *
 * Conflict discipline (Section 13.2 rollback): a `VERSION_CONFLICT` (or any
 * rejection) surfaces the catalog copy and invalidates the project query —
 * the refetched server truth flows back in through the `project` prop and
 * resets the fields via render-phase state adjustment (server truth wins).
 * NOTE: the project contract carries no `version` field (unlike tasks), so
 * the conflict path is simulated at the error boundary in tests; recorded as
 * a deviation in the changelog.
 */
export function EditProjectForm({ pid, project }: { pid: string; project: Project }) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState<FormValues>(() => toValues(project));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [feedback, setFeedback] = useState<{ kind: 'error' | 'success'; text: string } | null>(
    null,
  );

  // Server truth wins: whenever a refetched project arrives (after save or
  // conflict), the form rolls back to it — React's "adjust state when props
  // change" pattern, no effect involved.
  const [syncedProject, setSyncedProject] = useState(project);
  if (project !== syncedProject) {
    setSyncedProject(project);
    setValues(toValues(project));
    setErrors({});
  }

  const save = useMutation({
    mutationFn: (body: Partial<FormValues>) =>
      callApi(partialUpdateProject({ path: { pid }, body })),
    onSuccess: () => {
      setFeedback({ kind: 'success', text: 'Changes saved.' });
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(pid) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
    onError: (error) => {
      const friendly = resolveError(error);
      setFeedback({ kind: 'error', text: friendly.message });
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(pid) });
    },
  });

  function setField<K extends keyof FormValues>(key: K, value: string) {
    setFeedback(null);
    setValues((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fieldErrors = validateProjectFields(values);
    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) return;

    const baseline = toValues(project);
    const changed: Partial<FormValues> = {};
    for (const key of ['name', 'repo_path', 'default_branch'] as const) {
      if (values[key] !== baseline[key]) changed[key] = values[key];
    }
    if (Object.keys(changed).length === 0) {
      setFeedback({ kind: 'success', text: 'Nothing to save — no changes.' });
      return;
    }
    save.mutate(changed);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="grid max-w-lg gap-4">
      {feedback !== null && <FormBanner variant={feedback.kind}>{feedback.text}</FormBanner>}
      <FieldRow htmlFor="edit-name" label="Name" error={errors.name}>
        <Input
          id="edit-name"
          name="name"
          required
          value={values.name}
          aria-invalid={errors.name !== undefined}
          onChange={(event) => setField('name', event.target.value)}
        />
      </FieldRow>
      <FieldRow htmlFor="edit-repo-path" label="Repository path" error={errors.repo_path}>
        <Input
          id="edit-repo-path"
          name="repo_path"
          required
          value={values.repo_path}
          aria-invalid={errors.repo_path !== undefined}
          onChange={(event) => setField('repo_path', event.target.value)}
        />
      </FieldRow>
      <FieldRow htmlFor="edit-default-branch" label="Default branch" error={errors.default_branch}>
        <Input
          id="edit-default-branch"
          name="default_branch"
          required
          value={values.default_branch}
          aria-invalid={errors.default_branch !== undefined}
          onChange={(event) => setField('default_branch', event.target.value)}
        />
      </FieldRow>
      <div>
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save changes'}
        </Button>
      </div>
    </form>
  );
}
