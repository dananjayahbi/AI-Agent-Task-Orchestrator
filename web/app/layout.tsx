import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import { ThemeProvider } from 'next-themes';

export const metadata: Metadata = {
  title: 'AI Agent Task Orchestrator',
  description: 'Operations board for coordinating AI coding agents across repositories',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // suppressHydrationWarning: next-themes sets the theme class on <html>
    // before hydration (Section 13.4 dark/light themes).
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
