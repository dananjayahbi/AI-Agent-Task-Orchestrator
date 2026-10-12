import { PagePlaceholder } from '@/components/layout/page-placeholder';

/** Audit log (Section 13.1: filterable event history; WP-4.10). */
export default function AuditLogPage() {
  return (
    <PagePlaceholder
      title="Audit log"
      description="Filterable event history: state changes, token events, review decisions, logins, and policy edits."
    />
  );
}
