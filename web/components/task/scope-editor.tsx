'use client';

/**
 * Target-scope glob editor (MT-4.5-03; Section 13.2 "target-scope editor
 * with glob validation").
 *
 * Add/remove glob rows with per-entry validation from `glob-rules.ts`
 * (the WP-1.4 mirror). The panel always displays the current scope set —
 * these globs are the R2 Scope rule's input (Section 9.4) and the bound
 * on agent edits (RISK-04), so the operator must see exactly what is
 * stored; nothing is ever pre-filled (MT risk note: an over-broad
 * convenience default invites scope_violation storms).
 */
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type ScopeEditorProps = {
  entries: string[];
  onChange: (entries: string[]) => void;
  /** Per-index messages from `validateTargetScope` / server details. */
  errors: Record<number, string[]> | undefined;
  /** Count-cap message from `validateTargetScope`. */
  listError?: string | undefined;
};

export function ScopeEditor({ entries, onChange, errors, listError }: ScopeEditorProps) {
  function setEntry(index: number, value: string) {
    onChange(entries.map((entry, i) => (i === index ? value : entry)));
  }

  const displayed = entries.map((entry) => entry.trim()).filter((entry) => entry !== '');

  return (
    <div data-testid="scope-editor" className="grid gap-2">
      <p className="text-xs text-muted-foreground">
        Repo-relative globs bounding agent edits — the Policy Engine&apos;s R2 Scope rule checks
        every changed file against this set.
      </p>
      {listError !== undefined && (
        <p role="alert" className="text-xs text-destructive">
          {listError}
        </p>
      )}

      <ul className="grid gap-2" aria-label="Target scope globs">
        {entries.map((entry, index) => (
          <li key={index} className="grid gap-1">
            <div className="flex items-start gap-2">
              <Input
                aria-label={`Scope glob ${index + 1}`}
                value={entry}
                aria-invalid={errors?.[index] !== undefined}
                placeholder="src/api/**"
                className="font-mono text-sm"
                onChange={(event) => setEntry(index, event.target.value)}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                data-testid={`scope-remove-${index}`}
                aria-label={`Remove scope glob ${index + 1}`}
                onClick={() => onChange(entries.filter((_, i) => i !== index))}
              >
                Remove
              </Button>
            </div>
            {errors?.[index] !== undefined && (
              <ul role="alert" className="grid gap-0.5">
                {errors[index].map((problem) => (
                  <li key={problem} className="text-xs text-destructive">
                    {problem}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>

      <div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          data-testid="scope-add"
          onClick={() => onChange([...entries, ''])}
        >
          Add glob
        </Button>
      </div>

      {/* The saved-set mirror: what bounds the agent right now. */}
      <div
        data-testid="scope-current"
        aria-label="Current target scope"
        className="rounded-md border border-border bg-muted/30 p-2"
      >
        <p className="text-xs font-medium text-foreground">Current scope set</p>
        {displayed.length === 0 ? (
          <p data-testid="scope-current-empty" className="mt-1 text-xs text-muted-foreground">
            Empty — every changed file falls outside scope until globs are added.
          </p>
        ) : (
          <ul className="mt-1 flex flex-wrap gap-1">
            {displayed.map((glob) => (
              <li
                key={glob}
                className="rounded-full border border-border bg-background px-2 py-0.5 font-mono text-[11px] text-foreground"
              >
                {glob}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
