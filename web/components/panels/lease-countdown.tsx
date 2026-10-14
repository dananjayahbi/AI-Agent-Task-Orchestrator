/**
 * Reusable lease countdown (MT-4.9-02; Sections 13.1/13.2, 8.6, 9.6;
 * Principle P7).
 *
 * Computes remaining time from the server-issued `lease_expires_at`
 * against a server-aligned now (offset from live envelope anchors —
 * `lib/server-clock`) and ticks on the shared module timer (`useNow`, one
 * interval for every subscriber — the MT's 500-card regression guard).
 * It displays only: no lease → nothing (Section 20.3 "no zero-value
 * noise"); normal; warning at the Section 9.6 80%-of-lease signal, which
 * arrives both as the computed elapsed/total threshold and as the live
 * `task.lease_expiring` envelope (`expiring` — the server's own 80%
 * push); and "expired" while the sweeper has not yet cleared the lease
 * (formatting shared with the board badge — `formatLeaseRemaining`).
 *
 * Display-only, exactly like the board badge: it never guesses an
 * extension — the numbers come from server fields, so the Section 8.6
 * hard cap is mirrored, not re-implemented.
 */
import { formatLeaseRemaining } from '@/lib/board/lease';
import { useNow } from '@/lib/board/use-now';
import { useServerClockOffset } from '@/lib/server-clock';

type LeaseCountdownProps = {
  /** Section 7.2 `lease_acquired_at` — the 80% window's start. */
  acquiredAt: string | null;
  /** Section 7.2 `lease_expires_at` — the countdown target; null = no lease. */
  expiresAt: string | null;
  /** Live `task.lease_expiring` seen for this lease (Section 9.6 80% push). */
  expiring?: boolean;
};

export function LeaseCountdown({ acquiredAt, expiresAt, expiring = false }: LeaseCountdownProps) {
  const nowMs = useNow();
  const offset = useServerClockOffset();

  if (expiresAt === null) {
    return null; // no lease: nothing, not a zero (Section 20.3)
  }
  const expiresMs = Date.parse(expiresAt);
  if (Number.isNaN(expiresMs)) {
    return null;
  }

  const remainingMs = expiresMs - (nowMs + offset);
  const acquiredMs = acquiredAt === null ? Number.NaN : Date.parse(acquiredAt);
  const totalMs =
    Number.isNaN(acquiredMs) || expiresMs <= acquiredMs ? null : expiresMs - acquiredMs;
  const expired = remainingMs <= 0;
  // Section 9.6: the server pushes at 80% elapsed; the computed arm keeps
  // the same threshold when the envelope predates a reload/reconnect.
  const warning = !expired && (expiring || (totalMs !== null && remainingMs <= totalMs * 0.2));

  const state = expired ? 'expired' : warning ? 'warning' : 'remaining';
  const label = expired ? 'expired' : formatLeaseRemaining(remainingMs);
  const className = expired
    ? 'text-destructive'
    : warning
      ? 'text-amber-700 dark:text-amber-400'
      : 'text-muted-foreground';

  return (
    <span
      data-testid="lease-countdown"
      data-state={state}
      title={expired ? `Lease expired at ${expiresAt}` : `Lease expires at ${expiresAt}`}
      className={`text-xs ${className}`}
    >
      {label}
    </span>
  );
}
