import { OpsOverviewPanel } from '@/components/ops/ops-overview';

/**
 * Operations — the Section 17 Dashboards row (MT-6.4-03; NFR-10): the one
 * view an operator opens when something might be wrong — metrics, alert
 * firing states and health in a single owner-scoped snapshot. Own route
 * (app/ops), deliberately separate from the per-project Section 13 surfaces.
 */
export default function OpsPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Operations</h1>
        <p className="text-sm text-muted-foreground">
          Metrics, alert states and health — one snapshot for the operator on duty.
        </p>
      </div>
      <OpsOverviewPanel />
    </div>
  );
}
