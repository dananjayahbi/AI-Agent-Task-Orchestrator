/**
 * Dependencies-picker choice data (MT-4.5-04; Section 9.2 `GET
 * /projects/{pid}/tasks`; Section 13.4 performance posture).
 *
 * One page of the bound project's task list — **never** the whole set:
 * the picker loads the first page (the contract's documented default page
 * size, 25) and follows `next_cursor` only when the operator asks for
 * more. Zero-bleed is structural (Section 12.1): the query address is the
 * project's own list endpoint, so a cross-project task cannot enter the
 * choices even if a UI filter were bypassed.
 */
import { useInfiniteQuery } from '@tanstack/react-query';

import { callApi, listTasks } from '@/lib/api';
import type { Task } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

export const CHOICE_PAGE_SIZE = 25;

async function fetchChoicePage(
  pid: string,
  cursor: string | undefined,
): Promise<{
  tasks: Task[];
  nextCursor: string | null;
}> {
  const page = await callApi(
    listTasks({
      path: { pid },
      query: { page_size: CHOICE_PAGE_SIZE, ...(cursor === undefined ? {} : { cursor }) },
    }),
  );
  return { tasks: page.results, nextCursor: page.next_cursor };
}

/**
 * Lazily-paged dependency choices for one project. `enabled` ties the
 * fetch to the picker being open — a closed modal performs no network
 * work.
 */
export function useTaskChoicesQuery(pid: string, enabled: boolean) {
  return useInfiniteQuery({
    queryKey: queryKeys.taskChoices(pid),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => fetchChoicePage(pid, pageParam),
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled,
    staleTime: 30_000,
  });
}

/** Flattened choices in load order (deduped by id — cursor pages can repeat). */
export function flattenChoicePages(pages: readonly { tasks: Task[] }[] | undefined): Task[] {
  const seen = new Set<string>();
  const out: Task[] = [];
  for (const page of pages ?? []) {
    for (const task of page.tasks) {
      if (seen.has(task.id)) continue;
      seen.add(task.id);
      out.push(task);
    }
  }
  return out;
}

/** Case-insensitive id/title search over the loaded choices. */
export function matchChoice(task: Task, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (needle === '') return true;
  return task.id.toLowerCase().includes(needle) || task.title.toLowerCase().includes(needle);
}
