/**
 * Agents panel (MT-4.9-01; Section 13.1 "Live sessions, current leases,
 * countdowns, stalled markers").
 *
 * Sessions are project-scoped (both contract sources are: task leases
 * under `/projects/{pid}/tasks`, history under `GET /events?project=`),
 * so the panel carries its own project selector with the same preselect
 * rule as the chrome switcher — the last selected project from
 * localStorage, falling back to the first project. The selection is
 * derived during render (explicit choice → stored → first) so no effect
 * sets state; the effect only persists the choice to the external store.
 * `SessionsView` is mounted per selected project (`key`) so query and
 * stream state reset cleanly on a context switch.
 */
'use client';

import { useEffect, useState, useSyncExternalStore, type ChangeEvent } from 'react';

import { CURRENT_PROJECT_STORAGE_KEY } from '@/components/projects/project-switcher';
import { ErrorState } from '@/components/errors/error-state';
import { SessionsView } from '@/components/panels/sessions-view';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import { resolveError } from '@/lib/errors';
import { useProjectsQuery } from '@/lib/queries/projects';

function readStoredProject(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(CURRENT_PROJECT_STORAGE_KEY);
}

function subscribeStoredProject(onStoreChange: () => void): () => void {
  window.addEventListener('storage', onStoreChange);
  return () => window.removeEventListener('storage', onStoreChange);
}

export function AgentsPanel() {
  const projects = useProjectsQuery();
  const [selected, setSelected] = useState<string | null>(null);
  const storedPid = useSyncExternalStore(
    subscribeStoredProject,
    readStoredProject,
    () => null as string | null,
  );

  const list = projects.data ?? [];
  const preferred =
    storedPid !== null && list.some((project) => project.id === storedPid)
      ? storedPid
      : (list[0]?.id ?? '');
  const pid =
    selected !== null && list.some((project) => project.id === selected) ? selected : preferred;

  // Persist the active selection: the chrome switcher preselects from this
  // key on pages without a project route (same rule as MT-4.2-01).
  useEffect(() => {
    if (pid !== '' && readStoredProject() !== pid) {
      window.localStorage.setItem(CURRENT_PROJECT_STORAGE_KEY, pid);
    }
  }, [pid]);

  if (projects.isPending) {
    return <LoadingState label="Loading projects…" />;
  }

  if (projects.isError) {
    const friendly = resolveError(projects.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void projects.refetch()}
      />
    );
  }

  if (list.length === 0) {
    return (
      <EmptyState
        title="No projects yet"
        description="Agent sessions are tracked per project — create a project first."
      />
    );
  }

  function handleProjectChange(event: ChangeEvent<HTMLSelectElement>) {
    const next = event.target.value;
    if (next === '') return;
    setSelected(next);
  }

  return (
    <div data-testid="agents-page" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Agents</h1>
          <p className="text-sm text-muted-foreground">
            Live sessions, current leases and lease countdowns for the selected project.
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Project</span>
          <select
            aria-label="Project"
            data-testid="agents-project-select"
            value={pid}
            onChange={handleProjectChange}
            className="h-9 max-w-64 rounded-md border border-border bg-background px-2 text-sm text-foreground"
          >
            {list.map((project) => (
              <option key={project.id} value={project.id}>
                {project.id} — {project.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {pid !== '' && <SessionsView key={pid} pid={pid} />}
    </div>
  );
}
