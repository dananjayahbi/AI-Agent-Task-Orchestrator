/**
 * Checkpoint progress cache (MT-4.3-02 / MT-4.3-05; Section 13.2 percent
 * bar; Section 8.6 stalled indicator inputs).
 *
 * The tasks list contract (Section 9.2 `GET /projects/{pid}/tasks`) carries
 * `last_checkpoint_at` but **no percent** — the latest percent a board card
 * can show comes from `task.checkpoint` events (Section 9.6), which the
 * cache patcher (MT-4.3-05) writes here. There is deliberately no network
 * fetch behind this entry: percent-less cards render an explicit "unknown"
 * bar (MT-4.3-02 risk note) rather than pretending 0 % was reported.
 */
import { useQuery } from '@tanstack/react-query';

import { queryKeys } from '@/lib/queries/keys';

export type CheckpointProgressEntry = {
  /** Checkpoint percent 0-100, or null when the agent reported none. */
  percent: number | null;
  /** `occurred_at` of the checkpoint event that produced this entry. */
  at: string;
};

export type CheckpointProgressMap = Record<string, CheckpointProgressEntry>;

/**
 * Cache shell for the per-task progress map. The data itself is written by
 * the stream patcher via `setQueryData`; this hook only owns the cache
 * entry's identity and lifecycle (`staleTime: Infinity` — the stream is
 * the only writer).
 */
export function useCheckpointProgressQuery(pid: string) {
  return useQuery<CheckpointProgressMap>({
    queryKey: queryKeys.boardCheckpointProgress(pid),
    queryFn: async () => ({}),
    staleTime: Infinity,
  });
}
