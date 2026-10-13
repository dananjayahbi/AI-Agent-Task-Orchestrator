'use client';

/**
 * Dependencies picker (MT-4.5-04; Section 13.2 "dependencies picker").
 *
 * The Owner's window into the task graph that T2 (publish) and T4 (claim)
 * guard on (Section 8.2). Rules encoded here:
 *  - project scoping is structural: choices come from the bound
 *    project's own list endpoint (zero-bleed, Section 12.1) and the
 *    picker adds self/duplicate guards on top;
 *  - choices load lazily, one page at a time (Section 13.4) — no eager
 *    full-project fetch, search runs over what is loaded;
 *  - each selected dependency shows its current state, so "why can't I
 *    publish/claim?" is answerable before the server says so;
 *  - cycles are the server's to reject (WP-1.4 validates existence, self
 *    and cycles on every write and rolls the whole change back); the
 *    client keeps only the obvious self-guard — recorded in the WP
 *    changelog.
 */
import { useState } from 'react';
import { useQueries } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { isApiError } from '@/lib/api';
import { STATE_LABELS } from '@/lib/board/states';
import { resolveError } from '@/lib/errors';
import { fetchTaskRow } from '@/lib/queries/tasks';
import { flattenChoicePages, matchChoice, useTaskChoicesQuery } from '@/lib/queries/task-choices';

type DependenciesPickerProps = {
  pid: string;
  /** The task being edited — never pickable as its own dependency. */
  selfTaskId: string | null;
  dependsOn: string[];
  onChange: (dependsOn: string[]) => void;
};

/** State badge for one selected dependency (T2/T4 visibility, Section 8.2). */
function DependencyChip({
  pid,
  taskId,
  onRemove,
}: {
  pid: string;
  taskId: string;
  onRemove: () => void;
}) {
  const [row] = useQueries({
    queries: [
      {
        queryKey: ['projects', pid, 'tasks', taskId, 'row'] as const,
        queryFn: () => fetchTaskRow(taskId),
        staleTime: 30_000,
      },
    ],
  });

  let badge: { text: string; muted: boolean };
  if (row.isPending) {
    badge = { text: 'loading…', muted: true };
  } else if (row.isError) {
    // Friendly catalog copy (Section 13.3) — never the raw envelope.
    badge = {
      text: isApiError(row.error) ? resolveError(row.error).title : 'unavailable',
      muted: true,
    };
  } else {
    const state = row.data.state;
    badge = { text: STATE_LABELS[state] ?? state, muted: state === 'completed' };
  }

  return (
    <li
      data-testid={`dependency-chip-${taskId}`}
      className="flex items-center gap-1.5 rounded-full border border-border bg-background px-2 py-0.5 text-xs"
    >
      <span className="font-mono text-foreground">{taskId}</span>
      <span
        data-testid={`dependency-chip-state-${taskId}`}
        className={badge.muted ? 'text-muted-foreground' : 'font-medium text-foreground'}
      >
        {badge.text}
      </span>
      <button
        type="button"
        data-testid={`dependency-remove-${taskId}`}
        aria-label={`Remove dependency ${taskId}`}
        onClick={onRemove}
        className="rounded-full px-1 text-muted-foreground hover:text-destructive focus-visible:outline-2 focus-visible:outline-ring"
      >
        ×
      </button>
    </li>
  );
}

export function DependenciesPicker({
  pid,
  selfTaskId,
  dependsOn,
  onChange,
}: DependenciesPickerProps) {
  const [search, setSearch] = useState('');
  const { data, hasNextPage, fetchNextPage, isFetchingNextPage } = useTaskChoicesQuery(pid, true);
  const choices = flattenChoicePages(data?.pages);

  const selected = new Set(dependsOn);
  const results = choices.filter(
    (task) => task.id !== selfTaskId && !selected.has(task.id) && matchChoice(task, search),
  );

  return (
    <div data-testid="dependencies-picker" className="grid gap-2">
      <Input
        aria-label="Search tasks to add as dependencies"
        data-testid="dependencies-search"
        placeholder="Search by id or title (loads one page at a time)."
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />

      {dependsOn.length > 0 && (
        <ul aria-label="Current dependencies" className="flex flex-wrap gap-1.5">
          {dependsOn.map((taskId) => (
            <DependencyChip
              key={taskId}
              pid={pid}
              taskId={taskId}
              onRemove={() => onChange(dependsOn.filter((id) => id !== taskId))}
            />
          ))}
        </ul>
      )}

      <ul aria-label="Dependency choices" className="grid max-h-48 gap-1 overflow-y-auto">
        {results.length === 0 && (
          <li data-testid="dependencies-empty" className="text-xs text-muted-foreground">
            {choices.length === 0
              ? 'No tasks loaded yet.'
              : 'No loaded task matches the search (load more pages or refine it).'}
          </li>
        )}
        {results.map((task) => (
          <li key={task.id}>
            <button
              type="button"
              data-testid={`dependency-add-${task.id}`}
              onClick={() => onChange([...dependsOn, task.id])}
              className="w-full rounded-md border border-border px-2.5 py-1.5 text-left hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
            >
              <span className="block font-mono text-[11px] text-muted-foreground">{task.id}</span>
              <span className="block truncate text-sm text-foreground">{task.title}</span>
            </button>
          </li>
        ))}
      </ul>

      {hasNextPage && (
        <div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            data-testid="dependencies-load-more"
            disabled={isFetchingNextPage}
            onClick={() => void fetchNextPage()}
          >
            {isFetchingNextPage ? 'Loading…' : 'Load more tasks'}
          </Button>
        </div>
      )}
    </div>
  );
}
