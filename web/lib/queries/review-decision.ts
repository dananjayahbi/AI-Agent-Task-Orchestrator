/**
 * Review-decision mutation (MT-4.4-03 + MT-4.4-04; Section 9.2
 * `POST /tasks/{id}/review`, Section 13.2 optimistic UI with rollback).
 *
 * One mutation drives both dialogs (approve-merge, request-changes /
 * reassign):
 *
 *  1. `onMutate` — cancel nothing exotic: apply the optimistic patch to
 *     the exact board cache entry the dialog was opened from (Section
 *     13.2 "move appears instantly"; T15 only flips the merge-pending
 *     badge — Section 8.1);
 *  2. send the body built by `lib/review/review-decision` — the `version`
 *     the dialog saw (Section 8.2 rule 3) and, for approve, the viewed
 *     `resolution_id` (MT-3.6-04 stale protection);
 *  3. `onSuccess` — settle from the response's post-transition identity;
 *     the SSE `review.decided` refetch (WP-4.3 cache patching) confirms
 *     the same row idempotently (event wins after confirmation);
 *  4. `onError` — roll back to **server truth** by refetching the row
 *     (refresh beats restore-from-memory; another actor may have moved
 *     the card meanwhile), falling back to the snapshot only if that
 *     refresh fails, and announce the catalog-mapped message —
 *     `VERSION_CONFLICT` and `TASK_STATE_CONFLICT` map to distinct
 *     friendly copy (Section 13.3), never raw envelope text (G-07).
 *
 * The dialog stays open on failure (Section 13.3) — only success closes
 * it, via `onSettled` after the announcement.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { callApi, submitReviewDecision } from '@/lib/api';
import type { DecisionEnum, Task } from '@/lib/api/generated/types.gen';
import { matchesServerFilters, serverFiltersOf, type BoardFilters } from '@/lib/board/filters';
import { mergeRefetchedTask } from '@/lib/board/patch';
import { resolveError } from '@/lib/errors';
import { queryKeys } from '@/lib/queries/keys';
import { fetchTaskRow } from '@/lib/queries/tasks';
import { optimisticDecisionPatch, settleDecisionPatch } from '@/lib/review/optimistic';
import { decisionSuccessNotice, reviewBody } from '@/lib/review/review-decision';

export type ReviewDecisionInput = {
  /** The row the operator saw — its `version` is what gets sent. */
  task: Task;
  decision: DecisionEnum;
  /** Mandatory for `request_changes` (validated before submit). */
  note?: string;
  /** The resolution the dialog displayed (required for `approve`). */
  resolutionId?: string;
};

export type ReviewNotice = { message: string; rejected: boolean };

type MutationContext = {
  key: readonly unknown[];
  snapshot: Task[] | undefined;
};

/** The mutation shape the dialogs consume (typed hand-off, no `any`). */
export type ReviewDecisionMutation = ReturnType<typeof useReviewDecision>;

type UseReviewDecisionOptions = {
  pid: string;
  /** The board filters the dialog was opened under (targets the entry). */
  filters: BoardFilters;
  /** Board `role="status"` announcer (Section 13.4 — text outcomes). */
  onNotice: (notice: ReviewNotice) => void;
  /** Called after a successful decision — the dialogs close here. */
  onSuccess?: () => void;
};

export function useReviewDecision({ pid, filters, onNotice, onSuccess }: UseReviewDecisionOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: ReviewDecisionInput) => {
      const body = reviewBody(input.decision, input.task.version, {
        note: input.note,
        resolutionId: input.resolutionId,
      });
      return callApi(submitReviewDecision({ path: { id: input.task.id }, body }));
    },

    onMutate: (input): MutationContext => {
      const server = serverFiltersOf(filters);
      const key = queryKeys.boardTasks(pid, server);
      const snapshot = queryClient.getQueryData<Task[]>(key);
      queryClient.setQueryData<Task[]>(key, (tasks) =>
        tasks === undefined
          ? tasks
          : optimisticDecisionPatch(tasks, input.task.id, input.decision, input.note ?? ''),
      );
      return { key, snapshot };
    },

    onError: (error, _input, context) => {
      const friendly = resolveError(error);
      const refreshNote =
        friendly.code === 'VERSION_CONFLICT' || friendly.code === 'TASK_STATE_CONFLICT'
          ? ' The board now shows the server’s current state.'
          : '';
      // Server truth first: re-read the row, never trust the pre-move
      // snapshot alone (MT-4.4-04 risk note).
      void (async () => {
        if (context !== undefined) {
          try {
            const row = await fetchTaskRow(_input.task.id);
            const server = serverFiltersOf(filters);
            queryClient.setQueryData<Task[]>(context.key, (tasks) =>
              tasks === undefined ? tasks : mergeRefetchedTask(tasks, row, server),
            );
            return;
          } catch {
            // Fall through to the snapshot — a failed refresh must not
            // strand the optimistic row on screen.
          }
          const { key, snapshot } = context;
          if (snapshot !== undefined) {
            queryClient.setQueryData(key, snapshot);
          }
        }
      })();
      onNotice({
        message: `${friendly.title}: ${friendly.message}${refreshNote}`,
        rejected: true,
      });
    },

    onSuccess: (data, input) => {
      const server = serverFiltersOf(filters);
      const key = queryKeys.boardTasks(pid, server);
      queryClient.setQueryData<Task[]>(key, (tasks) => {
        if (tasks === undefined) {
          return tasks;
        }
        const settled = settleDecisionPatch(tasks, input.task.id, data.task);
        // Re-apply the active filters: a row that no longer matches (or
        // now matches) must sit where the server filter expects it
        // (MT-4.3-03 discipline).
        return settled.filter((task) => matchesServerFilters(task, server));
      });
      onNotice({ message: decisionSuccessNotice(input.decision, input.task.id), rejected: false });
      onSuccess?.();
    },
  });
}
