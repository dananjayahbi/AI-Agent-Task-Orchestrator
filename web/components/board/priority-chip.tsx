/**
 * Priority chip (MT-4.3-02; Section 7.2 priority enum — exactly four
 * values). Styling rides the MT-4.1-04 theme tokens only: `urgent` is the
 * one destructive-tinted chip, the rest step down the neutral scale.
 */
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from 'cn';
import type { PriorityEnum } from '@/lib/api/generated/types.gen';

const priorityChipVariants = cva(
  'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide',
  {
    variants: {
      priority: {
        urgent: 'bg-destructive text-destructive-foreground',
        high: 'bg-primary text-primary-foreground',
        medium: 'bg-secondary text-secondary-foreground',
        low: 'bg-muted text-muted-foreground',
      },
    },
    defaultVariants: {
      priority: 'medium',
    },
  },
);

type PriorityChipProps = {
  priority: PriorityEnum;
} & VariantProps<typeof priorityChipVariants>;

export function PriorityChip({ priority }: PriorityChipProps) {
  return (
    <span
      data-testid={`priority-chip-${priority}`}
      aria-label={`Priority ${priority}`}
      className={cn(priorityChipVariants({ priority }))}
    >
      {priority}
    </span>
  );
}
