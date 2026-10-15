'use client';

/**
 * Evidence commands block (MT-4.8-02; Section 10.5 evidence shape,
 * Section 13.2 review panel "evidence commands with exit codes").
 *
 * Shows the Section 10.5 fields the panel renders inline — each command
 * with its verbatim exit code and `lint_clean` — and collapses every
 * other key of the backend-owned evidence JSON behind a disclosure: the
 * blob may carry more (stats, engine details) than the panel knows,
 * which stays visible-but-collapsed rather than dropped or reinterpreted
 * (MT risk note). A non-object blob degrades to an explicit "no
 * structured evidence" note, never an empty table.
 */
import { parseEvidence } from '@/lib/review/evidence';

export function EvidenceBlock({ evidence }: { evidence: unknown }) {
  const parsed = parseEvidence(evidence);
  if (parsed === null) {
    return (
      <p data-testid="review-evidence-empty" className="text-xs text-muted-foreground">
        No structured evidence recorded with this report.
      </p>
    );
  }

  const extraKeys = Object.keys(parsed.extraFields);
  return (
    <div data-testid="review-evidence" className="grid gap-2">
      <h4 className="text-sm font-semibold text-foreground">Evidence</h4>
      <p data-testid="review-evidence-lint" className="text-xs text-muted-foreground">
        Lint clean:{' '}
        {parsed.lintClean === null ? (
          <span className="text-muted-foreground">not recorded</span>
        ) : parsed.lintClean ? (
          <span className="font-semibold text-emerald-700 dark:text-emerald-400">Yes</span>
        ) : (
          <span className="font-semibold text-destructive">No</span>
        )}
      </p>

      {parsed.commands.length === 0 ? (
        <p data-testid="review-evidence-commands-empty" className="text-xs text-muted-foreground">
          No commands recorded with this report.
        </p>
      ) : (
        <ul data-testid="review-evidence-commands" className="grid gap-1.5">
          {parsed.commands.map((command, index) => (
            <li
              key={`${command.command}-${index}`}
              data-testid="review-evidence-command"
              className="rounded-md border border-border bg-muted/30 p-2 text-xs"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span
                  data-testid={`review-evidence-label-${index}`}
                  className="font-semibold text-foreground"
                >
                  {command.label}
                </span>
                <span
                  data-testid={`review-evidence-exit-${index}`}
                  className={`font-mono font-semibold ${
                    command.exitCode === 0
                      ? 'text-emerald-700 dark:text-emerald-400'
                      : 'text-destructive'
                  }`}
                >
                  exit {command.exitCode ?? 'unknown'}
                </span>
              </div>
              <code className="mt-0.5 block break-all font-mono text-[11px] text-muted-foreground">
                {command.command}
              </code>
              {command.summary !== null && (
                <p className="mt-1 text-muted-foreground">{command.summary}</p>
              )}
            </li>
          ))}
        </ul>
      )}

      {extraKeys.length > 0 && (
        <details data-testid="review-evidence-extra" className="text-xs">
          <summary className="cursor-pointer text-muted-foreground">
            Additional evidence fields
          </summary>
          <pre className="mt-1 overflow-x-auto rounded-md border border-border bg-muted/30 p-2 font-mono text-[11px] text-muted-foreground">
            {JSON.stringify(parsed.extraFields, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
