/**
 * Shared loading pattern (MT-4.1-04; Section 13.4 consistency) — feature WPs
 * reuse this for route transitions and pending data.
 */
export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-2 text-muted-foreground">
      <span
        aria-hidden="true"
        className="size-4 animate-spin rounded-full border-2 border-border border-t-foreground"
      />
      <span className="text-sm">{label}</span>
    </div>
  );
}
