'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { cn } from 'cn';

import { layout } from '@/lib/layout/styles';

type NavItem = {
  href: string;
  label: string;
};

/**
 * Primary navigation for the Section 13.1 routes (MT-4.1-01; styled per
 * MT-4.1-04). Active state follows the current path so feature WPs inherit a
 * consistent shell.
 */
const NAV_ITEMS: NavItem[] = [
  { href: '/', label: 'Overview' },
  { href: '/projects', label: 'Projects' },
  { href: '/review', label: 'Review queue' },
  { href: '/agents', label: 'Agents' },
  { href: '/audit-log', label: 'Audit log' },
  { href: '/ops', label: 'Operations' },
  { href: '/settings', label: 'Settings' },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className={layout.appNav}>
      {NAV_ITEMS.map((item) => {
        const active =
          item.href === '/'
            ? pathname === '/'
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm transition-colors',
              active
                ? 'bg-accent font-medium text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
