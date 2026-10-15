import type { Project } from '@/lib/api';

import { cn } from 'cn';

/**
 * Canonical project status chip (MT-4.2-01 risk note: values come from
 * Section 8/FR-PRJ-04's active | paused | archived triple — no invented
 * intermediate states).
 */
const STATUS_STYLE: Record<Project['active_status'], string> = {
  active: 'border-transparent bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
  paused: 'border-transparent bg-amber-500/15 text-amber-800 dark:text-amber-400',
  archived: 'border-transparent bg-muted text-muted-foreground',
};

export function StatusBadge({ status }: { status: Project['active_status'] }) {
  return (
    <span
      data-status={status}
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize',
        STATUS_STYLE[status],
      )}
    >
      {status}
    </span>
  );
}
