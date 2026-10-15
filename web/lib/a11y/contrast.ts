/**
 * WCAG contrast math (MT-4.11-03; NFR-13 / WCAG 2.1 AA, SC 1.4.3 and
 * 1.4.11).
 *
 * One pure, dependency-free implementation of the contrast pipeline so
 * the accessibility audit's token assertions run against the values
 * that actually ship: parse the oklch colours out of `globals.css`,
 * convert each to an sRGB luminance, and compare pairs against the AA
 * thresholds. No layout or DOM required — the same numbers a browser
 * computes for text/UI contrast, minus the rounding.
 *
 * Conversion chain (https://www.w3.org/TR/css-color-4/#oklch):
 * oklch(L C H) → oklab(L a b) → LMS' → LMS → linear sRGB → gamma
 * encode → WCAG relative luminance → contrast ratio.
 */

/** sRGB gamma decode one channel to linear light (WCAG/IEC 61966-2-1). */
function gammaDecode(encoded: number): number {
  const c = Math.min(1, Math.max(0, encoded));
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

/** sRGB gamma encode one linear channel (WCAG/IEC 61966-2-1). */
function gammaEncode(channel: number): number {
  const clamped = Math.min(1, Math.max(0, channel));
  return clamped <= 0.0031308 ? 12.92 * clamped : 1.055 * Math.pow(clamped, 1 / 2.4) - 0.055;
}

/**
 * WCAG relative luminance of an *encoded* sRGB triplet (0–1 each).
 * Channels are linearized first — WCAG's formula operates on linear
 * light, not the gamma-encoded code values.
 */
export function relativeLuminance([r, g, b]: readonly [number, number, number]): number {
  return 0.2126 * gammaDecode(r) + 0.7152 * gammaDecode(g) + 0.0722 * gammaDecode(b);
}

/**
 * WCAG contrast ratio (1–21) between two encoded-sRGB colours.
 * Order-insensitive.
 */
export function contrastRatio(
  fg: readonly [number, number, number],
  bg: readonly [number, number, number],
): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const hi = Math.max(l1, l2);
  const lo = Math.min(l1, l2);
  return (hi + 0.05) / (lo + 0.05);
}

/**
 * One oklch colour → encoded sRGB. `lightness`/`chroma` are the oklch
 * 0–1 / 0–~0.4 scales; `hueDegrees` the angle. Out-of-gamut channels
 * clamp (WCAG contrast of the displayable colour is what matters).
 */
export function oklchToSrgb(
  lightness: number,
  chroma: number,
  hueDegrees: number,
): [number, number, number] {
  const h = (hueDegrees * Math.PI) / 180;
  const a = chroma * Math.cos(h);
  const b = chroma * Math.sin(h);

  // oklab → LMS' (Björn Ottosson's matrices).
  const l_ = lightness + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = lightness - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = lightness - 0.0894841775 * a - 1.291485548 * b;

  const l3 = l_ * l_ * l_;
  const m3 = m_ * m_ * m_;
  const s3 = s_ * s_ * s_;

  // LMS → linear sRGB.
  const lr = 4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3;
  const lg = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3;
  const lb = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.707614701 * s3;

  return [gammaEncode(lr), gammaEncode(lg), gammaEncode(lb)];
}

/** WCAG 1.4.3 threshold for normal-size body text. */
export const AA_TEXT_RATIO = 4.5;
/** WCAG 1.4.11 threshold for focus indicators and other UI components. */
export const AA_NON_TEXT_RATIO = 3;
