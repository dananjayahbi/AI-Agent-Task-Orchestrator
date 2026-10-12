import type { ReactNode } from 'react';

import { Label } from '@/components/ui/label';
import { cn } from 'cn';

type FieldRowProps = {
  htmlFor: string;
  label: string;
  error?: string | undefined;
  hint?: string;
  children: ReactNode;
};

/**
 * Label + control + validation message (MT-4.2-02 shared form pattern —
 * Section 13.3: identical error placement across create, edit and policy
 * forms).
 */
export function FieldRow({ htmlFor, label, error, hint, children }: FieldRowProps) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error !== undefined && error !== '' && (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
      {error === undefined && hint !== undefined && (
        <p className="text-xs text-muted-foreground">{hint}</p>
      )}
    </div>
  );
}

/** Wrapper for form-level feedback (server errors, save success). */
export function FormBanner({
  variant,
  children,
}: {
  variant: 'error' | 'success';
  children: ReactNode;
}) {
  return (
    <p
      role={variant === 'error' ? 'alert' : 'status'}
      data-variant={variant}
      className={cn(
        'rounded-md border px-3 py-2 text-sm',
        variant === 'error'
          ? 'border-destructive/40 bg-destructive/10 text-destructive'
          : 'border-border bg-muted text-foreground',
      )}
    >
      {children}
    </p>
  );
}
