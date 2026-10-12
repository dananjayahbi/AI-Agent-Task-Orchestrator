import { ProjectList } from '@/components/projects/project-list';

/**
 * Overview — all projects as status cards (Section 13.1; MT-4.2-01). The
 * card fields are exactly what `GET /projects` returns today (id, name,
 * status); active-agent/throughput metrics arrive with the dashboard
 * endpoint in later WP work rather than being invented here.
 */
export default function OverviewPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Overview</h1>
        <p className="text-sm text-muted-foreground">
          All projects: status cards for this workspace.
        </p>
      </div>
      <ProjectList />
    </div>
  );
}
