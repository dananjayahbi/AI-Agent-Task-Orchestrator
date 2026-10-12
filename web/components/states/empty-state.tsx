import type { ReactNode } from 'react';

type EmptyStateProps = {
  title: string;
  description?: string;
  /** Optional call-to-action slot (a Button from the caller). */
  action?: ReactNode;
};

/**
 * Shared empty pattern (MT-4.1-04; Section 13.4) — feature WPs reuse it for
 * zero-result boards, queues and lists.
 */
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-border p-8 text-center">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description !== undefined && (
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      )}
      {action !== undefined && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
