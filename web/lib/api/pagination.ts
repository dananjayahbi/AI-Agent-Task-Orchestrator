/**
 * Cursor-page collection (MT-4.2-01; Section 9.2 cursor pagination,
 * docs/plan/conventions/pagination.md: pass `next_cursor` until it is null).
 *
 * Generic over the page shape so every list endpoint can reuse it; the caller
 * supplies a closure that runs the generated sdk for one page — this helper
 * knows nothing about endpoints (NFR-11 import boundary).
 */
export type CursorPage<T> = {
  results: T[];
  next_cursor: string | null;
};

/** Defensive cap: a misbehaving server cannot loop the client forever. */
const MAX_PAGES = 100;

export async function fetchAllPages<T>(
  fetchPage: (cursor: string | undefined) => Promise<CursorPage<T>>,
): Promise<T[]> {
  const all: T[] = [];
  const seen = new Set<string>();
  let cursor: string | undefined;

  for (let guard = 0; guard < MAX_PAGES; guard += 1) {
    const page = await fetchPage(cursor);
    all.push(...page.results);
    if (page.next_cursor === null) {
      return all;
    }
    // Repeated cursor would loop forever — stop rather than spin.
    if (seen.has(page.next_cursor)) {
      return all;
    }
    seen.add(page.next_cursor);
    cursor = page.next_cursor;
  }
  return all;
}
