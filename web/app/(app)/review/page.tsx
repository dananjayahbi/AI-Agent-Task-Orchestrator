import { ReviewQueue } from '@/components/review/review-queue';

/**
 * Review queue (Section 13.1: all in_human_review tasks across projects,
 * sorted by age and priority; MT-4.8-01).
 */
export default function ReviewQueuePage() {
  return <ReviewQueue />;
}
