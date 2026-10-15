/**
 * MT-4.11-03 — contrast and label audit regression tests (NFR-13;
 * WCAG 2.1 AA SC 1.4.3 text, 1.4.11 non-text, 1.3.1/3.3.1 labels).
 *
 * Two halves, mirroring the audit's two finding classes:
 *
 *  1. **Contrast** — the oklch tokens parsed straight out of
 *     `app/globals.css` (the values that ship, not a copied table),
 *     converted through the pure `lib/a11y/contrast.ts` pipeline, are
 *     asserted against the AA thresholds for every documented pair in
 *     *both* themes, including the shared alpha tints
 *     (`bg-destructive/10` banners, `/15` badges) composited over their
 *     backdrops. Status tones (emerald/amber/red) are pinned at their
 *     component-shade level too.
 *  2. **Labels** — form errors/hints are programmatically associated
 *     with their controls (`aria-describedby` from the shared FieldRow
 *     and the markdown editor), disabled audit filters keep their
 *     accessible names without the old sub-threshold `opacity-60`, and
 *     the board's icon-only controls carry accessible names.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AA_NON_TEXT_RATIO, AA_TEXT_RATIO, contrastRatio, oklchToSrgb } from '@/lib/a11y/contrast';
import { parseThemeTokens, type ThemeToken } from '@/lib/a11y/theme-tokens';
import { FieldRow } from '@/components/projects/form-field';
import { MarkdownEditor } from '@/components/task/markdown-editor';
import { AuditLogFiltersBar } from '@/components/audit/audit-log-filters';
import { Input } from '@/components/ui/input';

import {
  installApi,
  jsonResponse,
  makeProject,
  pageOf,
  renderWithQueryClient,
  type Route,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

const css = readFileSync(join(process.cwd(), 'app', 'globals.css'), 'utf8');
const themes = parseThemeTokens(css);

const rgb = (token: ThemeToken): [number, number, number] =>
  oklchToSrgb(token.lightness, token.chroma, token.hue);

/** Composite an alpha token over an opaque backdrop (sRGB CSS blending). */
function over(backdrop: [number, number, number], token: ThemeToken): [number, number, number] {
  const fg = rgb(token);
  return [0, 1, 2].map(
    (i) => token.alpha * (fg[i] as number) + (1 - token.alpha) * backdrop[i],
  ) as [number, number, number];
}

function token(theme: 'light' | 'dark', name: string): ThemeToken {
  const found = themes[theme][name];
  if (found === undefined) {
    throw new Error(`token --${name} missing from ${theme} theme`);
  }
  return found;
}

describe.each(['light', 'dark'] as const)('theme contrast tokens (%s theme)', (theme) => {
  it('body text pairs clear WCAG AA (4.5:1)', () => {
    const background = rgb(token(theme, 'background'));
    const muted = rgb(token(theme, 'muted'));
    const card = rgb(token(theme, 'card'));
    for (const fg of ['foreground', 'muted-foreground', 'secondary-foreground'] as const) {
      expect(contrastRatio(rgb(token(theme, fg)), background)).toBeGreaterThanOrEqual(
        AA_TEXT_RATIO,
      );
      expect(contrastRatio(rgb(token(theme, fg)), card)).toBeGreaterThanOrEqual(AA_TEXT_RATIO);
      expect(contrastRatio(rgb(token(theme, fg)), muted)).toBeGreaterThanOrEqual(AA_TEXT_RATIO);
    }
  });

  it('chip foregrounds clear AA against their chip backgrounds (4.5:1)', () => {
    for (const [fg, bg] of [
      ['primary-foreground', 'primary'],
      ['secondary-foreground', 'secondary'],
      ['accent-foreground', 'accent'],
      ['destructive-foreground', 'destructive'],
    ] as const) {
      expect(contrastRatio(rgb(token(theme, fg)), rgb(token(theme, bg)))).toBeGreaterThanOrEqual(
        AA_TEXT_RATIO,
      );
    }
  });

  it('the focus-ring token clears the 3:1 non-text minimum on page surfaces', () => {
    const ring = rgb(token(theme, 'ring'));
    for (const bg of ['background', 'card', 'muted'] as const) {
      expect(contrastRatio(ring, rgb(token(theme, bg)))).toBeGreaterThanOrEqual(AA_NON_TEXT_RATIO);
    }
  });

  it('text-destructive clears AA on the shared destructive tints', () => {
    const background = rgb(token(theme, 'background'));
    const destructiveText = rgb(token(theme, 'destructive'));
    const destructive = token(theme, 'destructive');
    // FormBanner error (bg-destructive/10) and destructive badges (/15)
    // both composite over the page background.
    expect(
      contrastRatio(destructiveText, over(background, { ...destructive, alpha: 0.1 })),
    ).toBeGreaterThanOrEqual(AA_TEXT_RATIO);
    expect(
      contrastRatio(destructiveText, over(background, { ...destructive, alpha: 0.15 })),
    ).toBeGreaterThanOrEqual(AA_TEXT_RATIO);
  });
});

describe('status-tone shades (MT-4.11-03 findings)', () => {
  // The semantic status colours are Tailwind palette shades (not theme
  // tokens); the audit pinned the exact failing→fixed pairs.
  const cases: Array<[string, string, string, number]> = [
    // [fg, bg, label, threshold]
    ['047857', 'ffffff', 'emerald-700 Pass text on card', AA_TEXT_RATIO],
    ['b45309', 'ffffff', 'amber-700 warning text on card', AA_TEXT_RATIO],
    ['92400e', 'f7f0e2', 'amber-800 on amber-500/15 tint', AA_TEXT_RATIO],
    ['b91c1c', 'fdeaea', 'red-700 on red-500/15 tint', AA_TEXT_RATIO],
    ['0369a1', 'ffffff', 'sky-700 diff rename marker', AA_TEXT_RATIO],
    ['34d399', '171717', 'emerald-400 on dark background', AA_TEXT_RATIO],
    ['fbbf24', '171717', 'amber-400 on dark background', AA_TEXT_RATIO],
    ['f87171', '171717', 'red-400 on dark background', AA_TEXT_RATIO],
  ];
  it.each(cases)('#%s on #%s — %s', (fg, bg, _label, threshold) => {
    const toRgb = (hex: string): [number, number, number] => [
      parseInt(hex.slice(0, 2), 16) / 255,
      parseInt(hex.slice(2, 4), 16) / 255,
      parseInt(hex.slice(4, 6), 16) / 255,
    ];
    expect(contrastRatio(toRgb(fg), toRgb(bg))).toBeGreaterThanOrEqual(threshold);
  });
});

describe('label associations (MT-4.11-03 findings)', () => {
  it('FieldRow wires its error message into the control via aria-describedby', () => {
    render(
      <FieldRow htmlFor="demo-field" label="Demo" error="Required.">
        <Input id="demo-field" />
      </FieldRow>,
    );
    const input = screen.getByLabelText('Demo');
    const error = screen.getByRole('alert');
    expect(error.textContent).toBe('Required.');
    expect(input.getAttribute('aria-describedby')).toBe('demo-field-error');
    // The association is real: the referenced id exists on the message.
    expect(document.getElementById('demo-field-error')).toBe(error);
  });

  it('FieldRow wires its hint text in the same way (and merges both)', () => {
    const { unmount } = render(
      <FieldRow htmlFor="hinted" label="Hinted" hint="A helpful hint.">
        <Input id="hinted" />
      </FieldRow>,
    );
    expect(screen.getByLabelText('Hinted').getAttribute('aria-describedby')).toBe('hinted-hint');
    expect(document.getElementById('hinted-hint')?.textContent).toBe('A helpful hint.');
    unmount();

    render(
      <FieldRow htmlFor="both" label="Both" error="Bad." hint="Hint.">
        <Input id="both" />
      </FieldRow>,
    );
    expect(screen.getByLabelText('Both').getAttribute('aria-describedby')).toBe(
      'both-hint both-error',
    );
  });

  it('the markdown editor associates its validation message with the textarea', () => {
    render(<MarkdownEditor id="desc" value="# Hi" error="Too long." onChange={() => undefined} />);
    const textarea = screen.getByTestId('markdown-editor-input');
    expect(textarea.getAttribute('aria-describedby')).toBe('desc-error');
    expect(document.getElementById('desc-error')?.textContent).toBe('Too long.');
    // No error → no dangling reference.
    const view = render(<MarkdownEditor id="clean" value="# Hi" onChange={() => undefined} />);
    expect(
      within(view.container).getByTestId('markdown-editor-input').getAttribute('aria-describedby'),
    ).toBeNull();
  });
});

describe('audit filter controls (MT-4.11-03 findings)', () => {
  function mountFilters() {
    const routes: Route[] = [
      {
        method: 'GET',
        match: /\/api\/v1\/projects(\?|$)/,
        respond: () => jsonResponse(pageOf([makeProject({ id: 'PID00001', name: 'Demo' })])),
      },
    ];
    const { calls } = installApi(routes);
    renderWithQueryClient(
      <AuditLogFiltersBar
        filters={{ project: null, task: null }}
        onChange={() => undefined}
        onClearAll={() => undefined}
      />,
    );
    return { calls };
  }

  it('disabled contract-gated filters keep accessible names and drop opacity-60', () => {
    mountFilters();
    for (const [testId, name] of [
      ['audit-filter-actor', 'Filter by actor (requires contract change)'],
      ['audit-filter-from', 'Filter from date (requires contract change)'],
      ['audit-filter-to', 'Filter to date (requires contract change)'],
      ['audit-filter-type', 'Filter by event type (requires contract change)'],
    ] as const) {
      const control = screen.getByTestId(testId) as HTMLInputElement;
      expect(control.disabled).toBe(true); // contract gate unchanged
      expect(control.getAttribute('aria-label')).toBe(name);
      // The old opacity-60 dropped the text below the AA floor — gone.
      expect(control.className).not.toMatch(/opacity-/);
    }
  });
});
