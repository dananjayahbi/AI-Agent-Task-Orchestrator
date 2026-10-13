import { Board } from '@/components/board/board';

/**
 * Project board route (Section 13.1; WP-4.3 — MT-4.3-01 … MT-4.3-06 build
 * the six-column realtime Kanban; MT-4.4 will add drag-and-drop).
 */
export default async function ProjectBoardPage({ params }: { params: Promise<{ pid: string }> }) {
  const { pid } = await params;
  return <Board pid={pid} />;
}
