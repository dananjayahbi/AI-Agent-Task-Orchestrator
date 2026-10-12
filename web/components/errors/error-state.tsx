import { Button } from '@/components/ui/button';

type ErrorStateProps = {
  title: string;
  message: string;
  /** Envelope `correlation_id` shown for support — never internal detail. */
  requestId?: string;
  onRetry?: () => void;
};

/**
 * Full in-page error state (MT-4.1-04; Section 13.3) — the shared pattern
 * feature WPs (WP-4.2+) reuse for `state`-presentation failures. Renders only
 * catalog copy plus the reference id (G-07: no raw server text, no stack).
 */
export function ErrorState({ title, message, requestId, onRetry }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-6" role="alert">
      <h2 className="text-lg font-semibold text-card-foreground">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      {requestId !== undefined && requestId !== '' && (
        <p className="mt-2 text-xs text-muted-foreground">Reference ID: {requestId}</p>
      )}
      {onRetry !== undefined && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
