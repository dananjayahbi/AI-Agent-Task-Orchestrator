import Link from 'next/link';

import { StatusBadge } from '@/components/projects/status-badge';
import type { Project } from '@/lib/api';

/**
 * Project status card (MT-4.2-01; Section 13.1 Overview). Fields limited to
 * what `GET /projects` returns (id, name, status) — richer Overview metrics
 * (active agents, throughput) need `GET /dashboard/summary` and belong to
 * later dashboard work, not this slice.
 */
export function ProjectCard({ project }: { project: Project }) {
  return (
    <li className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{project.id}</p>
          <h3 className="truncate text-sm font-semibold text-card-foreground">
            <Link href={`/projects/${project.id}/board`} className="hover:underline">
              {project.name}
            </Link>
          </h3>
        </div>
        <StatusBadge status={project.active_status} />
      </div>
      <div className="mt-3 flex gap-3 text-xs">
        <Link
          href={`/projects/${project.id}/board`}
          className="text-muted-foreground hover:text-foreground hover:underline"
        >
          Board
        </Link>
        <Link
          href={`/projects/${project.id}/settings`}
          className="text-muted-foreground hover:text-foreground hover:underline"
        >
          Settings
        </Link>
      </div>
    </li>
  );
}
