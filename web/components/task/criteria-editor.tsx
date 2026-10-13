'use client';

/**
 * Acceptance-criteria list editor (MT-4.5-03; Section 13.2 "acceptance
 * criteria list editor").
 *
 * Ordered add/edit/remove over `TaskFormValues.acceptance_criteria` —
 * the array order is the display order, so round trips through save and
 * reload are exact (Section 20.3: structured list, not markdown).
 * Validation mirrors WP-1.4's stance (see `glob-rules.ts`): the list is
 * optional, blank rows are blocked until filled or removed.
 */
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

type CriteriaEditorProps = {
  entries: string[];
  onChange: (entries: string[]) => void;
  /** Per-index messages from `validateAcceptanceCriteria` / server details. */
  errors: Record<number, string> | undefined;
};

export function CriteriaEditor({ entries, onChange, errors }: CriteriaEditorProps) {
  function setEntry(index: number, value: string) {
    onChange(entries.map((entry, i) => (i === index ? value : entry)));
  }

  return (
    <div data-testid="criteria-editor" className="grid gap-2">
      {entries.length === 0 && (
        <p data-testid="criteria-editor-empty" className="text-xs text-muted-foreground">
          No acceptance criteria yet — the auditor verifies each criterion you add here, so add only
          what the task must satisfy.
        </p>
      )}
      <ol className="grid gap-2" aria-label="Acceptance criteria list">
        {entries.map((entry, index) => (
          <li key={index} className="grid gap-1">
            <div className="flex items-start gap-2">
              <span
                aria-hidden="true"
                className="mt-2 w-5 shrink-0 text-right font-mono text-xs text-muted-foreground"
              >
                {index + 1}.
              </span>
              <Textarea
                aria-label={`Criterion ${index + 1}`}
                value={entry}
                aria-invalid={errors?.[index] !== undefined}
                rows={2}
                onChange={(event) => setEntry(index, event.target.value)}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                data-testid={`criteria-remove-${index}`}
                aria-label={`Remove criterion ${index + 1}`}
                onClick={() => onChange(entries.filter((_, i) => i !== index))}
              >
                Remove
              </Button>
            </div>
            {errors?.[index] !== undefined && (
              <p role="alert" className="pl-7 text-xs text-destructive">
                {errors[index]}
              </p>
            )}
          </li>
        ))}
      </ol>
      <div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          data-testid="criteria-add"
          onClick={() => onChange([...entries, ''])}
        >
          Add criterion
        </Button>
      </div>
    </div>
  );
}
