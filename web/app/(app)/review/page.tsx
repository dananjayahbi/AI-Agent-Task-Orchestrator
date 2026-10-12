import { PagePlaceholder } from '@/components/layout/page-placeholder';

/**
 * Review queue (Section 13.1: all in_human_review tasks across projects,
 * sorted by age and priority; WP-4.7).
 */
export default function ReviewQueuePage() {
  return (
    <PagePlaceholder
      title="Review queue"
      description="All tasks awaiting human review across projects, sorted by age and priority."
    />
  );
}
