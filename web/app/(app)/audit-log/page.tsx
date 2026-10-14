import { AuditLog } from '@/components/audit/audit-log';

/**
 * Audit log (Section 13.1: filterable event history; WP-4.10). MT-4.10-01
 * renders the history; MT-4.10-02 adds the contract-mapped filters with
 * URL-synced state.
 */
export default function AuditLogPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Audit log</h1>
        <p className="text-sm text-muted-foreground">
          Read-only history of every recorded event — the log is append-only (Section 12.5).
        </p>
      </div>
      <AuditLog />
    </div>
  );
}
