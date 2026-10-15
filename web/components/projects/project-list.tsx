'use client';

import Link from 'next/link';

import { ProjectCard } from '@/components/projects/project-card';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/errors/error-state';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import { resolveError } from '@/lib/errors';
import { layout } from '@/lib/layout/styles';
import { useProjectsQuery } from '@/lib/queries/projects';

/**
 * Project list (MT-4.2-01; Section 13.1 Overview/Projects). The three
 * states are separated per Section 20.3: loading, empty (with the create
 * CTA that MT-4.2-02's form fulfils) and error — copy always comes from the
 * canonical catalog, never the raw server message (Section 13.3; G-07).
 */
export function ProjectList() {
  const projects = useProjectsQuery();

  if (projects.isPending) {
    return <LoadingState label="Loading projects…" />;
  }

  if (projects.isError) {
    const friendly = resolveError(projects.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void projects.refetch()}
      />
    );
  }

  if (projects.data.length === 0) {
    return (
      <EmptyState
        title="No projects yet"
        description="Create the first project to get a board, a manifest and agent tokens."
        action={
          <Button asChild>
            <Link href="/projects/new">Create a project</Link>
          </Button>
        }
      />
    );
  }

  return (
    <ul className={layout.cardGrid}>
      {projects.data.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </ul>
  );
}
