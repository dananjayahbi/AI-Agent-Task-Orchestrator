import { PagePlaceholder } from '@/components/layout/page-placeholder';

/**
 * Overview — all projects: status cards, active agents, tasks needing
 * attention, throughput (Section 13.1). This is the app's landing/board view
 * (MT-4.1-01): authenticated navigation and login both land here.
 */
export default function OverviewPage() {
  return (
    <PagePlaceholder
      title="Overview"
      description="All projects: status cards, active agents, tasks needing attention, and throughput."
    />
  );
}
