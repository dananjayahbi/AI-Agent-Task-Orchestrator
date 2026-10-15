/**
 * Stalled-task indicator for the Agents lease view (MT-4.9-03;
 * Sections 8.6, 13.1, 13.4).
 *
 * Section 8.6 defines "stalled" as UI-only: no checkpoint within
 * `stalled_after_minutes` while the lease is still valid — so this is the
 * same derivation the board card marker uses (`isTaskStalled`, shared
 * through `stallSubjectOf`) fed by the policy threshold passed in from
 * the view (no hard-coded 20 beyond the documented default). Stall ≠
 * expiry: an expired lease hides the marker (the sweeper's territory), a
 * fresh checkpoint clears it, and the lease row itself disappears on
 * lease end — all through recomputation, never a client-only flag.
 *
 * `last_checkpoint_at` semantics follow what WP-1.8 stores (every
 * accepted checkpoint kind touches the field — recorded in the WP
 * changelog), mirroring the board marker so the two surfaces never
 * disagree. A11y (Section 13.4): visible "Stalled" text with a title
 * tooltip stating the threshold — no icon-only state.
 */
import { isTaskStalled, DEFAULT_STALLED_AFTER_MINUTES } from '@/lib/board/stalled';
import { useNow } from '@/lib/board/use-now';
import { stallSubjectOf, type AgentSessionTaskJoin } from '@/lib/queries/agent-sessions';

type StalledIndicatorProps = {
  join: AgentSessionTaskJoin;
  /** Section 7.2 policy value (Section 13.3 — re-read live, never cached). */
  stalledAfterMinutes?: number;
};

export function StalledIndicator({ join, stalledAfterMinutes }: StalledIndicatorProps) {
  const nowMs = useNow();
  const stalled = isTaskStalled(
    stallSubjectOf(join),
    stalledAfterMinutes ?? DEFAULT_STALLED_AFTER_MINUTES,
    nowMs,
  );
  if (!stalled) {
    return null; // Section 20.3: before threshold, nothing shows
  }
  return (
    <span
      data-testid="stalled-indicator"
      title={`No checkpoint within stalled_after_minutes (${stalledAfterMinutes ?? DEFAULT_STALLED_AFTER_MINUTES} min)`}
      className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[11px] font-medium text-amber-800 dark:text-amber-400"
    >
      Stalled
    </span>
  );
}
