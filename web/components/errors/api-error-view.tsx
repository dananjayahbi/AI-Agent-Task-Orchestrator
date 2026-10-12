'use client';

import { ErrorState } from '@/components/errors/error-state';
import { resolveError } from '@/lib/errors';

/**
 * Presents a thrown error through the shared catalog (MT-4.1-04 wiring into
 * MT-4.1-02's routing: app/(app)/error.tsx renders this for every page
 * failure). `AUTH_FORBIDDEN_PROJECT` lands on its friendly denial state, an
 * expired session (`AUTH_REQUIRED`) has already been silently redirected by
 * the API seam, and anything unrecognised degrades to the generic state with
 * the reference id — never raw server text (G-07; Section 13.3).
 */
export function ApiErrorView({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  const friendly = resolveError(error);
  return (
    <ErrorState
      title={friendly.title}
      message={friendly.message}
      requestId={friendly.requestId === '' ? undefined : friendly.requestId}
      onRetry={onRetry}
    />
  );
}
