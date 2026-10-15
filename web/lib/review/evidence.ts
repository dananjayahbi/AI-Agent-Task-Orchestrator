/**
 * Evidence parsing (MT-4.8-02; Section 10.5 evidence shape carried on the
 * Audit Report's `evidence` JSON — Section 13.2 "evidence commands with
 * exit codes", Section 20.5).
 *
 * Renders the Section 10.5 fields the panel shows inline — `commands`
 * (label, command, exit code, optional summary) and `lint_clean` — and
 * hands everything else back as opaque fields for a collapsed disclosure:
 * the evidence blob is backend-owned JSON, so unknown keys must stay
 * visible-but-collapsed, never dropped and never reinterpreted (MT risk
 * note). A non-object blob parses to `null` — "no structured evidence".
 */

export type EvidenceCommand = {
  label: string;
  command: string;
  /** Exit code verbatim; null when the engine recorded none. */
  exitCode: number | null;
  summary: string | null;
};

export type ParsedEvidence = {
  commands: EvidenceCommand[];
  /** `lint_clean` when it is a boolean; null when absent/unparseable. */
  lintClean: boolean | null;
  /** Every key outside the inline-known set, preserved as-is. */
  extraFields: Record<string, unknown>;
};

const INLINE_KEYS = new Set(['commands', 'lint_clean']);

function normalizeCommand(entry: unknown, index: number): EvidenceCommand | null {
  if (typeof entry !== 'object' || entry === null) return null;
  const candidate = entry as Record<string, unknown>;
  const command = candidate['command'];
  if (typeof command !== 'string' || command === '') return null;
  const label = candidate['label'];
  const exitCode = candidate['exit_code'];
  const summary = candidate['summary'];
  return {
    label: typeof label === 'string' && label !== '' ? label : `command ${index + 1}`,
    command,
    exitCode: typeof exitCode === 'number' ? exitCode : null,
    summary: typeof summary === 'string' && summary !== '' ? summary : null,
  };
}

/** Parse the evidence blob; null when it is not a JSON object at all. */
export function parseEvidence(evidence: unknown): ParsedEvidence | null {
  if (typeof evidence !== 'object' || evidence === null || Array.isArray(evidence)) {
    return null;
  }
  const candidate = evidence as Record<string, unknown>;

  const commands: EvidenceCommand[] = [];
  if (Array.isArray(candidate['commands'])) {
    candidate['commands'].forEach((entry, index) => {
      const command = normalizeCommand(entry, index);
      if (command !== null) commands.push(command);
    });
  }

  const lintRaw = candidate['lint_clean'];
  const extraFields: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(candidate)) {
    if (!INLINE_KEYS.has(key)) extraFields[key] = value;
  }

  return {
    commands,
    lintClean: typeof lintRaw === 'boolean' ? lintRaw : null,
    extraFields,
  };
}
