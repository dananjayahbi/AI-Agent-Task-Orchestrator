'use client';

/**
 * Extension-based syntax highlighting (MT-4.7-02; Section 13.2 "syntax
 * highlighting"; FR-WEB-04).
 *
 * Deliberately tiny and dependency-free (recorded choice, MT risk
 * note): a per-line scanner with small grammar tables for the common
 * web/backend file types. Highlight grammars for exotic languages are
 * out of scope — **unmapped extensions fall back to plain text**, never
 * an error and never an invented mapping table (MT-4.7-02 risk note).
 *
 * Tokenization is per line (no multi-line state): a block comment or
 * template literal that spans lines only colors the portion on its
 * own line. That is a rendering-fidelity trade-off, not a contract
 * change — highlighting runs only for rows the virtualized view
 * mounts (RISK-13), so a 5,000-line patch never pays for lines nobody
 * can see.
 */

export type HighlightKind = 'plain' | 'keyword' | 'string' | 'comment' | 'number';

export type HighlightToken = {
  text: string;
  kind: HighlightKind;
};

/** A language grammar: line-comment marker, string quotes, keyword set. */
type Grammar = {
  lineComment: string | null;
  quotes: string;
  keywords: ReadonlySet<string>;
};

const JS_KEYWORDS = new Set([
  'async',
  'await',
  'break',
  'case',
  'catch',
  'class',
  'const',
  'continue',
  'default',
  'delete',
  'do',
  'else',
  'export',
  'extends',
  'false',
  'finally',
  'for',
  'from',
  'function',
  'get',
  'if',
  'import',
  'in',
  'instanceof',
  'let',
  'new',
  'null',
  'of',
  'return',
  'set',
  'static',
  'super',
  'switch',
  'this',
  'throw',
  'true',
  'try',
  'typeof',
  'undefined',
  'var',
  'void',
  'while',
  'yield',
]);

const JSON_KEYWORDS = new Set(['true', 'false', 'null']);

const PYTHON_KEYWORDS = new Set([
  'and',
  'as',
  'assert',
  'async',
  'await',
  'break',
  'class',
  'continue',
  'def',
  'del',
  'elif',
  'else',
  'except',
  'False',
  'finally',
  'for',
  'from',
  'global',
  'if',
  'import',
  'in',
  'is',
  'lambda',
  'None',
  'nonlocal',
  'not',
  'or',
  'pass',
  'raise',
  'return',
  'True',
  'try',
  'while',
  'with',
  'yield',
]);

const SHELL_KEYWORDS = new Set([
  'case',
  'do',
  'done',
  'elif',
  'else',
  'esac',
  'exit',
  'fi',
  'for',
  'function',
  'if',
  'in',
  'local',
  'read',
  'return',
  'set',
  'source',
  'then',
  'unset',
  'while',
]);

const YAML_KEYWORDS = new Set(['true', 'false', 'null', 'yes', 'no', 'on', 'off']);

/**
 * Extension → grammar. One explicit table (MT risk note: no invented
 * mappings — only languages with a real grammar entry are listed).
 */
const GRAMMARS: Record<string, Grammar> = {
  js: { lineComment: '//', quotes: '"\'`', keywords: JS_KEYWORDS },
  jsx: { lineComment: '//', quotes: '"\'`', keywords: JS_KEYWORDS },
  mjs: { lineComment: '//', quotes: '"\'`', keywords: JS_KEYWORDS },
  cjs: { lineComment: '//', quotes: '"\'`', keywords: JS_KEYWORDS },
  ts: { lineComment: '//', quotes: '"\'`', keywords: JS_KEYWORDS },
  tsx: { lineComment: '//', quotes: '"\'`', keywords: JS_KEYWORDS },
  mts: { lineComment: '//', quotes: '"\'`', keywords: JS_KEYWORDS },
  cts: { lineComment: '//', quotes: '"\'`', keywords: JS_KEYWORDS },
  json: { lineComment: null, quotes: '"', keywords: JSON_KEYWORDS },
  jsonc: { lineComment: '//', quotes: '"', keywords: JSON_KEYWORDS },
  py: { lineComment: '#', quotes: '"\'', keywords: PYTHON_KEYWORDS },
  pyw: { lineComment: '#', quotes: '"\'', keywords: PYTHON_KEYWORDS },
  sh: { lineComment: '#', quotes: '"\'', keywords: SHELL_KEYWORDS },
  bash: { lineComment: '#', quotes: '"\'', keywords: SHELL_KEYWORDS },
  zsh: { lineComment: '#', quotes: '"\'', keywords: SHELL_KEYWORDS },
  yml: { lineComment: '#', quotes: '"\'', keywords: YAML_KEYWORDS },
  yaml: { lineComment: '#', quotes: '"\'', keywords: YAML_KEYWORDS },
};

/** The grammar for a path's extension, or null → plain-text fallback. */
export function grammarForPath(path: string): Grammar | null {
  const dot = path.lastIndexOf('.');
  if (dot < 0 || dot === path.length - 1) return null;
  return GRAMMARS[path.slice(dot + 1).toLowerCase()] ?? null;
}

const WORD_START = /[A-Za-z_$]/;
const WORD_BODY = /[A-Za-z0-9_$]/;
const DIGIT = /[0-9]/;

/**
 * Tokenize one line against one grammar. Unknown grammar → a single
 * plain token (the documented fallback). Pure and allocation-light
 * enough for per-visible-row use.
 */
export function tokenizeLine(line: string, grammar: Grammar | null): HighlightToken[] {
  if (grammar === null || line === '') return [{ text: line, kind: 'plain' }];
  const tokens: HighlightToken[] = [];
  let plain = '';
  const flushPlain = () => {
    if (plain !== '') {
      tokens.push({ text: plain, kind: 'plain' });
      plain = '';
    }
  };

  let index = 0;
  while (index < line.length) {
    const char = line[index];

    // Line comment: consumes the rest of the line.
    if (grammar.lineComment !== null && line.startsWith(grammar.lineComment, index)) {
      flushPlain();
      tokens.push({ text: line.slice(index), kind: 'comment' });
      return tokens;
    }

    // String literal (naive: to the next unescaped matching quote on
    // this line; unterminated runs to end of line).
    if (grammar.quotes.includes(char)) {
      flushPlain();
      let end = index + 1;
      while (end < line.length) {
        if (line[end] === '\\') {
          end += 2;
          continue;
        }
        if (line[end] === char) {
          end += 1;
          break;
        }
        end += 1;
      }
      tokens.push({ text: line.slice(index, Math.min(end, line.length)), kind: 'string' });
      index = end;
      continue;
    }

    // Number literal (word-boundary guarded so `x1` is not a number).
    if (DIGIT.test(char) && (index === 0 || !WORD_BODY.test(line[index - 1]))) {
      flushPlain();
      let end = index + 1;
      while (end < line.length && /[0-9A-Fa-fxbo._]/.test(line[end])) end += 1;
      tokens.push({ text: line.slice(index, end), kind: 'number' });
      index = end;
      continue;
    }

    // Identifier: keyword or plain.
    if (WORD_START.test(char)) {
      let end = index + 1;
      while (end < line.length && WORD_BODY.test(line[end])) end += 1;
      const word = line.slice(index, end);
      flushPlain();
      tokens.push({ text: word, kind: grammar.keywords.has(word) ? 'keyword' : 'plain' });
      index = end;
      continue;
    }

    plain += char;
    index += 1;
  }
  flushPlain();
  return tokens;
}
