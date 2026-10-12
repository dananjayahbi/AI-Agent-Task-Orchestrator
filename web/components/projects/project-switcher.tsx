'use client';

import { useEffect, useSyncExternalStore, type ChangeEvent } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { useProjectsQuery } from '@/lib/queries/projects';

/**
 * Last selected project, persisted client-side (MT-4.2-01 scope: documented
 * storage choice — a project id is not a secret; no credentials involved).
 * The **route is the source of truth** whenever a `/projects/{pid}` segment
 * is present (MT-4.2-01 risk note): the stored value only preselects the
 * control on pages without a project context (Overview, Review, …) so a
 * reload keeps the selection.
 */
export const CURRENT_PROJECT_STORAGE_KEY = 'orchestrator.web.current-project';

const PROJECT_ROUTE = /^\/projects\/(PID\d{5})(?:\/|$)/;

export function pidFromPathname(pathname: string): string | null {
  return PROJECT_ROUTE.exec(pathname)?.[1] ?? null;
}

function readStoredProject(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(CURRENT_PROJECT_STORAGE_KEY);
}

function subscribeStoredProject(onStoreChange: () => void): () => void {
  window.addEventListener('storage', onStoreChange);
  return () => window.removeEventListener('storage', onStoreChange);
}

export function ProjectSwitcher() {
  const pathname = usePathname();
  const router = useRouter();
  const projects = useProjectsQuery();

  // External store over localStorage: survives reloads without a setState-
  // in-effect sync; the server snapshot stays null (no hydration mismatch).
  const storedPid = useSyncExternalStore(
    subscribeStoredProject,
    readStoredProject,
    () => null as string | null,
  );

  const routePid = pidFromPathname(pathname ?? '');

  // The route wins — mirror it into storage so pages without a project
  // context preselect the most recently visited project. Pure side effect,
  // no state sync: safe under StrictMode double-invocation.
  useEffect(() => {
    if (routePid !== null && routePid !== readStoredProject()) {
      window.localStorage.setItem(CURRENT_PROJECT_STORAGE_KEY, routePid);
    }
  }, [routePid]);

  if (projects.isPending || projects.isError || projects.data.length === 0) {
    // Chrome control, not a data surface: pages render their own states.
    return null;
  }

  const options = projects.data;
  const wanted = routePid ?? storedPid ?? options[0]?.id ?? '';
  const selected = options.some((project) => project.id === wanted) ? wanted : '';

  function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    const pid = event.target.value;
    if (pid === '') return;
    window.localStorage.setItem(CURRENT_PROJECT_STORAGE_KEY, pid);
    // Board route of the selected project — switching context = navigation.
    router.push(`/projects/${pid}/board`);
  }

  return (
    <label className="flex items-center gap-2 text-sm text-muted-foreground">
      <span className="sr-only">Current project</span>
      <select
        aria-label="Current project"
        data-testid="project-switcher"
        value={selected}
        onChange={handleChange}
        className="h-9 max-w-48 rounded-md border border-border bg-background px-2 text-sm text-foreground"
      >
        {selected === '' && (
          <option value="" disabled>
            Select a project
          </option>
        )}
        {options.map((project) => (
          <option key={project.id} value={project.id}>
            {project.id} — {project.name}
          </option>
        ))}
      </select>
    </label>
  );
}
