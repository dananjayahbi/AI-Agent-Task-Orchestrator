/**
 * Markdown tokenizer (MT-4.5-02; parent plan Section 13.2 "markdown
 * editor with preview", Section 12.1 P10 posture).
 *
 * A deliberately small block/inline parser producing a plain AST — the
 * preview renders this AST as React elements (never an HTML string, never
 * `dangerouslySetInnerHTML`), so embedded HTML/script in markdown cannot
 * execute: unknown constructs (including raw HTML) fall through as literal
 * text and React escapes them at render time.
 *
 * Deliberate scope limits (recorded in the WP changelog):
 *  - links render inert (label + URL as text) and images never fetch —
 *    the preview must not leak editor sessions to third parties (MT risk
 *    note); nothing here emits an `href` or `src` React attribute;
 *  - no task description is rewritten: this module is read-only parsing
 *    for display. Round-trip fidelity is the editor's textarea contract
 *    (save exactly what was typed).
 */

export type Inline =
  | { kind: 'text'; text: string }
  | { kind: 'code'; text: string }
  | { kind: 'bold'; children: Inline[] }
  | { kind: 'italic'; children: Inline[] }
  | { kind: 'link'; label: string; href: string }
  | { kind: 'image'; alt: string; src: string };

export type Block =
  | { kind: 'heading'; level: number; children: Inline[] }
  | { kind: 'paragraph'; children: Inline[] }
  | { kind: 'code'; lang: string; text: string }
  | { kind: 'quote'; lines: Inline[][] }
  | { kind: 'list'; ordered: boolean; items: Inline[][] }
  | { kind: 'hr' };

/**
 * Inline constructs, scanned left to right. Image before link so the `!`
 * of `![alt](src)` binds to the image rule, not the inner brackets.
 */
const INLINE_PATTERN =
  /(`+)([^`]*?)\1|\*\*([^*]+)\*\*|\*([^*]+)\*|!\[([^\]]*)\]\(([^)\s]*)\)|\[([^\]]+)\]\(([^)\s]*)\)/;

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  let rest = text;
  let plain = '';
  for (;;) {
    const match = INLINE_PATTERN.exec(rest);
    if (match === null) {
      plain += rest;
      break;
    }
    plain += rest.slice(0, match.index);
    const [whole, , codeText, boldText, italicText, imageAlt, imageSrc, linkLabel, linkHref] =
      match;
    if (codeText !== undefined) {
      out.push({ kind: 'text', text: plain });
      plain = '';
      out.push({ kind: 'code', text: codeText });
    } else if (boldText !== undefined) {
      out.push({ kind: 'text', text: plain });
      plain = '';
      out.push({ kind: 'bold', children: parseInline(boldText) });
    } else if (italicText !== undefined) {
      out.push({ kind: 'text', text: plain });
      plain = '';
      out.push({ kind: 'italic', children: parseInline(italicText) });
    } else if (imageAlt !== undefined && imageSrc !== undefined) {
      out.push({ kind: 'text', text: plain });
      plain = '';
      out.push({ kind: 'image', alt: imageAlt, src: imageSrc });
    } else if (linkLabel !== undefined && linkHref !== undefined) {
      out.push({ kind: 'text', text: plain });
      plain = '';
      out.push({ kind: 'link', label: linkLabel, href: linkHref });
    }
    rest = rest.slice(match.index + whole.length);
  }
  if (plain !== '' || out.length === 0) {
    if (plain !== '') out.push({ kind: 'text', text: plain });
  }
  return out;
}

const FENCE_PATTERN = /^```(\S*)\s*$/;
const HEADING_PATTERN = /^(#{1,6})\s+(.*)$/;
const HR_PATTERN = /^(-{3,}|\*{3,}|_{3,})\s*$/;
const QUOTE_PATTERN = /^>\s?(.*)$/;
const UL_ITEM_PATTERN = /^[-*]\s+(.*)$/;
const OL_ITEM_PATTERN = /^\d+[.)]\s+(.*)$/;

export function parseMarkdown(source: string): Block[] {
  const lines = source.split(/\r?\n/);
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? '';

    if (line.trim() === '') {
      index += 1;
      continue;
    }

    const fence = FENCE_PATTERN.exec(line);
    if (fence !== null) {
      const lang = fence[1] ?? '';
      const body: string[] = [];
      index += 1;
      while (index < lines.length && !/^```\s*$/.test(lines[index] ?? '')) {
        body.push(lines[index] ?? '');
        index += 1;
      }
      index += 1; // consume the closing fence (or run off the end)
      blocks.push({ kind: 'code', lang, text: body.join('\n') });
      continue;
    }

    const heading = HEADING_PATTERN.exec(line);
    if (heading !== null) {
      blocks.push({
        kind: 'heading',
        level: heading[1]?.length ?? 1,
        children: parseInline(heading[2] ?? ''),
      });
      index += 1;
      continue;
    }

    if (HR_PATTERN.test(line)) {
      blocks.push({ kind: 'hr' });
      index += 1;
      continue;
    }

    if (QUOTE_PATTERN.test(line)) {
      const lines2: Inline[][] = [];
      while (index < lines.length) {
        const quoted = QUOTE_PATTERN.exec(lines[index] ?? '');
        if (quoted === null) break;
        lines2.push(parseInline(quoted[1] ?? ''));
        index += 1;
      }
      blocks.push({ kind: 'quote', lines: lines2 });
      continue;
    }

    const ul = UL_ITEM_PATTERN.exec(line);
    const ol = OL_ITEM_PATTERN.exec(line);
    if (ul !== null || ol !== null) {
      const ordered = ol !== null;
      const itemPattern = ordered ? OL_ITEM_PATTERN : UL_ITEM_PATTERN;
      const items: Inline[][] = [];
      while (index < lines.length) {
        const item = itemPattern.exec(lines[index] ?? '');
        if (item === null) break;
        items.push(parseInline(item[1] ?? ''));
        index += 1;
      }
      blocks.push({ kind: 'list', ordered, items });
      continue;
    }

    const paragraph: Inline[] = [];
    while (index < lines.length) {
      const current = lines[index] ?? '';
      if (
        current.trim() === '' ||
        FENCE_PATTERN.test(current) ||
        HEADING_PATTERN.test(current) ||
        HR_PATTERN.test(current) ||
        QUOTE_PATTERN.test(current) ||
        UL_ITEM_PATTERN.test(current) ||
        OL_ITEM_PATTERN.test(current)
      ) {
        break;
      }
      if (paragraph.length > 0) paragraph.push({ kind: 'text', text: '\n' });
      paragraph.push(...parseInline(current));
      index += 1;
    }
    blocks.push({ kind: 'paragraph', children: paragraph });
  }

  return blocks;
}
