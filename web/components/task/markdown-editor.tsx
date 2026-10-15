'use client';

/**
 * Markdown editor with preview (MT-4.5-02; Section 13.2 "markdown editor
 * with preview").
 *
 * Dependency decision (recorded in the WP changelog per MT risk note):
 * **no new dependency** — the preview is the inert AST renderer in
 * `markdown-preview.tsx`. Off-the-shelf editors either rewrite markdown
 * on save (breaking the byte-identical round-trip guarantee) or render
 * HTML previews by default (an injection surface this WP refuses to
 * ship); a ~100-line tokenizer with a React-element renderer keeps the
 * preview safe by construction and the stored bytes untouched.
 *
 * The editor is a controlled textarea — `value`/`onChange` pass straight
 * through the modal's `TaskFormValues.description`, so what is typed is
 * exactly what is saved and reloaded (no normalization). The Edit ⇄
 * Preview toggle is a pair of focusable buttons (Section 13.4 keyboard
 * operation); preview rendering is lazy (only when the tab is active) so
 * long descriptions cost nothing during typing.
 */
import { useId, useState } from 'react';

import { MarkdownPreview } from '@/components/task/markdown-preview';
import { Textarea } from '@/components/ui/textarea';
import { cn } from 'cn';

type MarkdownEditorProps = {
  id: string;
  value: string;
  onChange: (value: string) => void;
  /** Validation feedback from the shared schemas (MT-4.5-01 discipline). */
  error?: string | undefined;
};

type EditorTab = 'edit' | 'preview';

export function MarkdownEditor({ id, value, onChange, error }: MarkdownEditorProps) {
  const [tab, setTab] = useState<EditorTab>('edit');
  const tabsId = useId();

  return (
    <div data-testid="markdown-editor" className="grid gap-2">
      <div role="tablist" aria-label="Description editor mode" className="flex gap-1">
        <MarkdownTab
          id={`${tabsId}-edit`}
          active={tab === 'edit'}
          label="Edit"
          onSelect={() => setTab('edit')}
        />
        <MarkdownTab
          id={`${tabsId}-preview`}
          active={tab === 'preview'}
          label="Preview"
          onSelect={() => setTab('preview')}
        />
      </div>

      {tab === 'edit' ? (
        <Textarea
          id={id}
          data-testid="markdown-editor-input"
          value={value}
          aria-invalid={error !== undefined}
          // MT-4.11-03: the validation message is announced with the
          // field (WCAG 3.3.1), not as unassociated alert text.
          aria-describedby={error !== undefined && error !== '' ? `${id}-error` : undefined}
          placeholder="Markdown description — headings, lists, code fences, **bold**, `code`."
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <div
          role="tabpanel"
          aria-labelledby={`${tabsId}-preview`}
          className="min-h-16 rounded-md border border-border bg-transparent"
        >
          <MarkdownPreview source={value} />
        </div>
      )}

      {error !== undefined && error !== '' && (
        <p id={`${id}-error`} role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

function MarkdownTab({
  id,
  active,
  label,
  onSelect,
}: {
  id: string;
  active: boolean;
  label: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      id={id}
      role="tab"
      aria-selected={active}
      data-testid={`markdown-tab-${label.toLowerCase()}`}
      tabIndex={active ? 0 : -1}
      onClick={onSelect}
      className={cn(
        'rounded-md border px-2.5 py-1 text-xs font-medium focus-visible:outline-2 focus-visible:outline-ring',
        active
          ? 'border-border bg-muted text-foreground'
          : 'border-transparent text-muted-foreground hover:bg-muted/60',
      )}
    >
      {label}
    </button>
  );
}
