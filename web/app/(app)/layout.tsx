import type { ReactNode } from 'react';

import Link from 'next/link';

import { AppNav } from '@/components/layout/app-nav';
import { SessionControls } from '@/components/layout/session-controls';
import { ThemeToggle } from '@/components/layout/theme-toggle';
import { ProjectSwitcher } from '@/components/projects/project-switcher';
import { QueryProvider } from '@/components/providers/query-provider';
import { SessionProvider } from '@/components/session/session-context';

/**
 * Protected app segment (MT-4.1-01): every Section 13.1 page except Login
 * lives under this layout. Route gating (unauthenticated → login with return
 * path) happens in proxy.ts (MT-4.1-02); the layout provides the app chrome —
 * navigation for all Section 13.1 routes plus session controls — finished
 * visually by MT-4.1-04. MT-4.2-01 adds the project switcher (header level)
 * and the query cache every feature WP shares (Section 13.3).
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <QueryProvider>
        <div className="flex min-h-svh flex-col">
          <header className="border-b border-border bg-card">
            <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-3">
              <div className="flex items-center gap-4">
                <Link href="/" className="text-sm font-semibold text-foreground">
                  AI Agent Task Orchestrator
                </Link>
                <ProjectSwitcher />
              </div>
              <AppNav />
              <div className="flex items-center gap-1">
                <SessionControls />
                <ThemeToggle />
              </div>
            </div>
          </header>
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
        </div>
      </QueryProvider>
    </SessionProvider>
  );
}
