/**
 * Theme-token extraction (MT-4.11-03).
 *
 * Reads the oklch colour tokens out of `globals.css` for the a11y
 * contrast assertions — the tests verify the values that actually ship,
 * not a copied table that could drift. Pure string parsing: one `:root`
 * block (light) and one `.dark` block, each `--name: oklch(L C H)` or
 * `--name: oklch(L C H / alpha)`. Alpha tokens are returned with their
 * `alpha` field (callers composite over a backdrop before comparing).
 */

export type ThemeToken = {
  lightness: number;
  chroma: number;
  hue: number;
  alpha: number;
};

export type ThemeTokens = {
  light: Record<string, ThemeToken>;
  dark: Record<string, ThemeToken>;
};

const OKLCH = /--([\w-]+):\s*oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:\/\s*([\d.]+)%\s*)?\)/;

function parseBlock(css: string, selector: string): Record<string, ThemeToken> {
  // The block runs from `selector {` to the next closing brace at depth 0.
  const start = css.indexOf(`${selector} {`);
  if (start === -1) {
    throw new Error(`theme-tokens: selector ${selector} not found`);
  }
  const body = css.slice(start + selector.length + 1, css.indexOf('}', start));
  const tokens: Record<string, ThemeToken> = {};
  for (const line of body.split(';')) {
    const match = OKLCH.exec(line);
    if (match === null) {
      continue;
    }
    tokens[match[1] as string] = {
      lightness: Number(match[2]),
      chroma: Number(match[3]),
      hue: Number(match[4]),
      alpha: match[5] === undefined ? 1 : Number(match[5]) / 100,
    };
  }
  return tokens;
}

export function parseThemeTokens(css: string): ThemeTokens {
  return { light: parseBlock(css, ':root'), dark: parseBlock(css, '.dark') };
}
