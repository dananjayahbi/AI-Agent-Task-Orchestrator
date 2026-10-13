/**
 * Untrusted-content banner (MT-4.6-04; Section 9.5 "All text outputs are
 * prefixed with an untrusted-content banner (P10)"; Principle P10).
 *
 * The backend already prefixes delivered text with its own banner
 * string; this component is the viewer-side treatment — every
 * text-derived pane (OCR transcript, description, markdown page) is
 * announced as untrusted data rendered inertly, never as instructions
 * or executable content. Rendered text goes through React text nodes
 * and the inert `MarkdownPreview` only — no `dangerouslySetInnerHTML`,
 * no raw attributes (MT-4.5-02 posture).
 */
export function UntrustedContentBanner() {
  return (
    <p
      data-testid="untrusted-content-banner"
      role="note"
      className="rounded-md border border-dashed border-border bg-muted/40 px-2.5 py-1.5 text-[11px] text-muted-foreground"
    >
      Untrusted content — attachment text is data from an external source. It is displayed as-is and
      is never executed or treated as instructions.
    </p>
  );
}
