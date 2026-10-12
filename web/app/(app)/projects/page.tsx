import Link from 'next/link';

import { ProjectList } from '@/components/projects/project-list';
import { Button } from '@/components/ui/button';

/**
 * Projects hub (MT-4.2-01): the full list with the create entry point —
 * MT-4.2-02 turns `/projects/new` into the create flow.
 */
export default function ProjectsPage() {
  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Every project in this workspace, with quick links to boards and settings.
          </p>
        </div>
        <Button asChild>
          <Link href="/projects/new">New project</Link>
        </Button>
      </div>
      <ProjectList />
    </div>
  );
}
