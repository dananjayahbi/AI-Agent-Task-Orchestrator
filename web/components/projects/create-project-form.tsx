'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';

import { FieldRow, FormBanner } from '@/components/projects/form-field';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { callApi, createProject, type Project } from '@/lib/api';
import { validateProjectFields, type FieldErrors } from '@/lib/forms/project-schemas';
import { resolveError } from '@/lib/errors';
import { queryKeys } from '@/lib/queries/keys';

type FormValues = {
  name: string;
  repo_path: string;
  default_branch: string;
  system_prompt_rules: string;
};

const EMPTY: FormValues = { name: '', repo_path: '', default_branch: '', system_prompt_rules: '' };

/**
 * Create-project form (MT-4.2-02; FR-PRJ-01). `POST /projects` assigns the
 * `PID` server-side — the success panel displays the backend-assigned id and
 * points at Project settings, where MT-4.2-03 continues the flow with the
 * manifest download. Creating invalidates the shared list so MT-4.2-01's
 * switcher and Overview pick the project up immediately.
 */
export function CreateProjectForm() {
  const queryClient = useQueryClient();
  const [values, setValues] = useState<FormValues>(EMPTY);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [created, setCreated] = useState<Project | null>(null);

  const create = useMutation({
    mutationFn: (body: FormValues) => callApi(createProject({ body })),
    onSuccess: (project) => {
      setServerError(null);
      setCreated(project);
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
    onError: (error) => {
      setServerError(resolveError(error).message);
    },
  });

  function setField<K extends keyof FormValues>(key: K, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fieldErrors = validateProjectFields(values);
    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) {
      setServerError(null);
      return;
    }
    create.mutate(values);
  }

  if (created !== null) {
    return (
      <div className="grid max-w-lg gap-4 rounded-lg border border-border bg-card p-6">
        <div>
          <h2 className="text-lg font-semibold text-card-foreground">Project created</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The server assigned this project id (FR-PRJ-01):
          </p>
          <p data-testid="created-pid" className="mt-2 font-mono text-base font-semibold">
            {created.id}
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link href={`/projects/${created.id}/settings?created=${created.id}`}>
              Continue to project settings
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/projects">Back to projects</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="grid max-w-lg gap-4">
      {serverError !== null && <FormBanner variant="error">{serverError}</FormBanner>}
      <FieldRow htmlFor="project-name" label="Name" error={errors.name}>
        <Input
          id="project-name"
          name="name"
          required
          value={values.name}
          aria-invalid={errors.name !== undefined}
          onChange={(event) => setField('name', event.target.value)}
        />
      </FieldRow>
      <FieldRow
        htmlFor="project-repo-path"
        label="Repository path"
        error={errors.repo_path}
        hint="Path as seen by the bridge host, for example /srv/repos/my-app."
      >
        <Input
          id="project-repo-path"
          name="repo_path"
          required
          value={values.repo_path}
          aria-invalid={errors.repo_path !== undefined}
          onChange={(event) => setField('repo_path', event.target.value)}
        />
      </FieldRow>
      <FieldRow
        htmlFor="project-default-branch"
        label="Default branch"
        error={errors.default_branch}
      >
        <Input
          id="project-default-branch"
          name="default_branch"
          required
          value={values.default_branch}
          aria-invalid={errors.default_branch !== undefined}
          onChange={(event) => setField('default_branch', event.target.value)}
        />
      </FieldRow>
      <FieldRow
        htmlFor="project-rules"
        label="Agent rules (optional)"
        hint="Markdown rules injected into every agent's rules block; editable later in Project settings."
      >
        <Textarea
          id="project-rules"
          name="system_prompt_rules"
          value={values.system_prompt_rules}
          onChange={(event) => setField('system_prompt_rules', event.target.value)}
        />
      </FieldRow>
      <div>
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? 'Creating…' : 'Create project'}
        </Button>
      </div>
    </form>
  );
}
