type PagePlaceholderProps = {
  title: string;
  description: string;
};

/**
 * Placeholder body for Section 13.1 routes (MT-4.1-01). Each route exists so
 * navigation is fixed; feature WPs (WP-4.2+) replace these with real content.
 */
export function PagePlaceholder({ title, description }: PagePlaceholderProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h2 className="text-lg font-semibold text-card-foreground">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      <p className="mt-4 text-xs text-muted-foreground">Coming in a later work package.</p>
    </div>
  );
}
