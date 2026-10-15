import type { ReactNode } from 'react';
import { cloneElement, isValidElement } from 'react';

import { Label } from '@/components/ui/label';
import { cn } from 'cn';

type FieldRowProps = {
  htmlFor: string;
  label: string;
  error?: string | undefined;
  hint?: string;
  children: ReactNode;
};

/** Minimal element shape for the aria-describedby clone in FieldRow. */
type DescribedElement = React.ReactElement<{ 'aria-describedby'?: string }>;

/**
 * Label + control + validation message (MT-4.2-02 shared form pattern —
 * Section 13.3: identical error placement across create, edit and policy
 * forms).
 *
 * MT-4.11-03 (NFR-13, WCAG 1.3.1/3.3.1): the hint and error paragraphs
 * carry stable ids (`{htmlFor}-hint` / `{htmlFor}-error`) and are wired
 * into the control's `aria-describedby` (merged when the control is a
 * single element) so assistive tech announces the message with the
 * field, not as an unassociated alert.
 */
export function FieldRow({ htmlFor, label, error, hint, children }: FieldRowProps) {
  const hasError = error !== undefined && error !== '';
  const hintId = `${htmlFor}-hint`;
  const errorId = `${htmlFor}-error`;
  const describedBy =
    [hint !== undefined ? hintId : null, hasError ? errorId : null].filter(Boolean).join(' ') ||
    undefined;
  const control =
    describedBy !== undefined && isValidElement(children)
      ? cloneElement(children as DescribedElement, { 'aria-describedby': describedBy })
      : children;
  return (
    <div className="grid gap-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {control}
      {hasError && (
        <p id={errorId} role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
      {error === undefined && hint !== undefined && (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
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
