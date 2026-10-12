'use client';

import { ApiErrorView } from '@/components/errors/api-error-view';

/**
 * Error fallback for the protected segment (MT-4.1-02): any `ApiError`
 * thrown while rendering a page lands here and is presented from its
 * canonical code — `AUTH_FORBIDDEN_PROJECT` renders the friendly
 * project-access-denied state (G-07), never raw server text (MT-4.1-04
 * owns the presentation table this delegates to).
 */
export default function AppErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-lg py-10">
      <ApiErrorView error={error} onRetry={reset} />
    </div>
  );
}
