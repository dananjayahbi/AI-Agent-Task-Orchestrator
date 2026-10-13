'use client';

/**
 * Markdown preview renderer (MT-4.5-02; P10 posture; Section 12.1
 * injection row).
 *
 * Renders the `lib/forms/markdown` AST as React elements. Inert by
 * construction: no `dangerouslySetInnerHTML`, no `href`/`src` attributes —
 * links show their URL as text and images render as a labelled
 * placeholder, so hostile markdown (raw HTML/script, tracking pixels)
 * cannot execute or fetch (MT-4.5-02 risk notes). Dark/light theming
 * follows the shared token classes like every other surface (13.4).
 */
import type { Block, Inline } from '@/lib/forms/markdown';
import { parseMarkdown } from '@/lib/forms/markdown';
import { cn } from 'cn';

function InlineView({ nodes }: { nodes: Inline[] }) {
  return (
    <>
      {nodes.map((node, index) => {
        switch (node.kind) {
          case 'text':
            return <span key={index}>{node.text}</span>;
          case 'code':
            return (
              <code
                key={index}
                className="rounded bg-muted px-1 py-0.5 font-mono text-[0.9em] text-foreground"
              >
                {node.text}
              </code>
            );
          case 'bold':
            return (
              <strong key={index} className="font-semibold text-foreground">
                <InlineView nodes={node.children} />
              </strong>
            );
          case 'italic':
            return (
              <em key={index} className="italic text-foreground">
                <InlineView nodes={node.children} />
              </em>
            );
          case 'link':
            // Inert: the URL is shown as text, never as a clickable href
            // (no navigation/leak from the editor session).
            return (
              <span key={index} className="text-foreground">
                {node.label}{' '}
                <span className="text-muted-foreground">({node.href || 'no link target'})</span>
              </span>
            );
          case 'image':
            // Never fetch: render a labelled placeholder instead of <img>.
            return (
              <span
                key={index}
                data-testid="markdown-preview-image"
                className="rounded border border-dashed border-border px-1 py-0.5 text-xs text-muted-foreground"
              >
                Image: {node.alt || 'description missing'}
                {node.src !== '' ? ` (${node.src} — not fetched in preview)` : ''}
              </span>
            );
        }
      })}
    </>
  );
}

const HEADING_CLASSES: Record<number, string> = {
  1: 'text-lg font-bold',
  2: 'text-base font-bold',
  3: 'text-base font-semibold',
  4: 'text-sm font-semibold',
  5: 'text-sm font-medium',
  6: 'text-xs font-medium',
};

function BlockView({ block }: { block: Block }) {
  switch (block.kind) {
    case 'heading': {
      // Preview lives inside a dialog that already owns h1/h2 — headings
      // render as h3..h6 with level 5/6 folding onto h6.
      const Level = (['h3', 'h4', 'h5', 'h6', 'h6', 'h6'] as const)[
        Math.min(6, Math.max(1, block.level)) - 1
      ];
      return (
        <Level
          data-testid={`markdown-preview-h${block.level}`}
          className={cn('text-foreground', HEADING_CLASSES[block.level])}
        >
          <InlineView nodes={block.children} />
        </Level>
      );
    }
    case 'paragraph':
      return (
        <p className="text-sm leading-6 break-words text-foreground">
          <InlineView nodes={block.children} />
        </p>
      );
    case 'code':
      return (
        <pre
          data-testid="markdown-preview-code"
          className="overflow-x-auto rounded-md border border-border bg-muted/50 p-3 text-xs text-foreground"
        >
          <code className="font-mono">{block.text}</code>
        </pre>
      );
    case 'quote':
      return (
        <blockquote className="border-l-2 border-border pl-3 text-sm italic text-muted-foreground">
          {block.lines.map((line, index) => (
            <p key={index}>
              <InlineView nodes={line} />
            </p>
          ))}
        </blockquote>
      );
    case 'list':
      return block.ordered ? (
        <ol className="list-decimal pl-5 text-sm text-foreground">
          {block.items.map((item, index) => (
            <li key={index}>
              <InlineView nodes={item} />
            </li>
          ))}
        </ol>
      ) : (
        <ul className="list-disc pl-5 text-sm text-foreground">
          {block.items.map((item, index) => (
            <li key={index}>
              <InlineView nodes={item} />
            </li>
          ))}
        </ul>
      );
    case 'hr':
      return <hr className="border-border" />;
  }
}

export function MarkdownPreview({ source }: { source: string }) {
  const blocks = source.trim() === '' ? [] : parseMarkdown(source);
  if (blocks.length === 0) {
    return (
      <p data-testid="markdown-preview-empty" className="text-sm text-muted-foreground">
        Nothing to preview yet.
      </p>
    );
  }
  return (
    <div
      data-testid="markdown-preview"
      className="grid gap-2 rounded-md border border-border bg-background/40 p-3"
    >
      {blocks.map((block, index) => (
        <BlockView key={index} block={block} />
      ))}
    </div>
  );
}
