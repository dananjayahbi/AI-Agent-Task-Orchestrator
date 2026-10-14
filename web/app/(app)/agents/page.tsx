'use client';

import { AgentsPanel } from '@/components/panels/agents-panel';

/**
 * Agents (Section 13.1: live sessions, current leases, countdowns, stalled
 * markers; WP-4.9). The panel resolves its project context itself — the
 * route carries no project segment (13.1 route table).
 */
export default function AgentsPage() {
  return <AgentsPanel />;
}
