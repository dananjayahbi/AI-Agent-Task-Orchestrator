'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';

import { Button } from '@/components/ui/button';

/**
 * Light/dark toggle (MT-4.1-04; Section 13.4 "dark and light themes").
 * Icon choice is pure CSS (`dark:` variant follows the class next-themes
 * sets on <html>) so the markup is hydration-stable; the click handler reads
 * the current theme straight from the document — no render-cycle state.
 */
export function ThemeToggle() {
  const { setTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="Toggle color theme"
      onClick={() =>
        setTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark')
      }
    >
      <Moon className="size-4 dark:hidden" />
      <Sun className="size-4 hidden dark:block" />
    </Button>
  );
}
