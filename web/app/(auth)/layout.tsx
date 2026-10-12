import type { ReactNode } from 'react';

/**
 * Auth segment (MT-4.1-01): public routes — only the Login page lives here
 * (Section 13.1). Route protection for everything else is the (app) segment's
 * concern (MT-4.1-02).
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return <div className="flex min-h-svh items-center justify-center p-6">{children}</div>;
}
