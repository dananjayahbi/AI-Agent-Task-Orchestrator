'use client';

/**
 * Policy rule table (MT-4.8-02; Section 9.4 table, Section 13.2 review
 * panel "rule table", Section 20.5).
 *
 * Renders the parsed persisted `policy_rule_results` rows verbatim —
 * every Section 9.4 R1–R9 rule in plan order with its stored outcome.
 * A failing row shows the rule's review reason: the row's own persisted
 * `review_reason` when present (friendly label + verbatim code, Section
 * 8.4 discipline), falling back to the Section 9.4 mapping for that rule
 * id. Nothing is computed here — pass/fail is exactly what the engine
 * persisted (Section 9.4 authority note).
 *
 * Empty input renders nothing: the caller owns the fallback copy so a
 * pre-engine report never masquerades as an "all pass" table (MT risk
 * note).
 */
import { reviewReasonLabel } from '@/lib/review/review-reasons';
import type { RuleTableRow } from '@/lib/review/rule-results';

function reasonCell(row: RuleTableRow) {
  if (row.passed) {
    return <span className="text-muted-foreground">—</span>;
  }
  const reason = row.persistedReason ?? row.mappedReason;
  if (reason === null) {
    return <span className="text-muted-foreground">Not specified</span>;
  }
  return (
    <span data-testid={`review-rule-reason-${row.rule}`}>
      {reviewReasonLabel(reason)}
      <span className="font-mono text-[11px] text-muted-foreground"> ({reason})</span>
    </span>
  );
}

export function RuleTable({ rows }: { rows: readonly RuleTableRow[] }) {
  if (rows.length === 0) {
    return null;
  }
  return (
    <div data-testid="review-rule-table" className="grid gap-2">
      <h4 className="text-sm font-semibold text-foreground">Policy rules</h4>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground">
              <th scope="col" className="py-1.5 pr-3 font-semibold">
                Rule
              </th>
              <th scope="col" className="py-1.5 pr-3 font-semibold">
                Outcome
              </th>
              <th scope="col" className="py-1.5 font-semibold">
                Review reason
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.rule}
                data-testid={`review-rule-row-${row.rule}`}
                className="border-b border-border/60 align-top"
              >
                <th scope="row" className="py-1.5 pr-3 text-left font-normal">
                  <span className="font-mono text-xs font-semibold text-foreground">
                    {row.rule}
                  </span>
                  {row.label !== null && (
                    <span className="ml-1.5 text-xs text-muted-foreground">{row.label}</span>
                  )}
                </th>
                <td
                  data-testid={`review-rule-outcome-${row.rule}`}
                  data-passed={String(row.passed)}
                  className={`py-1.5 pr-3 text-xs font-semibold ${
                    row.passed ? 'text-emerald-700 dark:text-emerald-400' : 'text-destructive'
                  }`}
                >
                  {row.passed ? 'Pass' : 'Fail'}
                </td>
                <td className="py-1.5 text-xs">{reasonCell(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
