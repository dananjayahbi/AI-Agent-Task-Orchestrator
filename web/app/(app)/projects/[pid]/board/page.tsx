import { PagePlaceholder } from '@/components/layout/page-placeholder';

/** Project board — kanban for one project (Section 13.1; WP-4.3 builds it). */
export default async function ProjectBoardPage({ params }: { params: Promise<{ pid: string }> }) {
  const { pid } = await params;
  return (
    <PagePlaceholder
      title={`Board — ${pid}`}
      description="Kanban board for this project: six canonical-state columns, filters, search, and archive toggle."
    />
  );
}
