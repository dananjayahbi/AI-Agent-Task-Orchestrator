"""Secret-like pattern scan of added lines (parent plan Sections 9.4 rule R5,
10.8, 12.4; MT-2.10-04).

A read-only local scanner over the **added lines** of the merge-base diff
(MT-2.10-03's evidence bundle): it flags credential-shaped material before or
during submission, giving the agent a chance to stop a leak, and supplies
corroborating evidence for Policy Engine rule R5 (``sensitive_config_changed``
— the backend computes the ``sensitive_config_globs`` half from the stored
patch; this is the added-line "env/key patterns" half, Section 9.4).

Properties the plan fixes:

* *added lines only* — unchanged and removed lines are never scanned (a
  removed secret is not a new leak; a context line is not the agent's doing);
* *redacted excerpts* — a finding never echoes the matched secret material
  (Section 12.4: logs and output scrub secrets); the matched span is replaced
  by ``[REDACTED:<pattern id>]`` and the remainder is clipped;
* *configuration, not code* — the default pattern set ships as a TOML data
  file (``secret_patterns.toml``); :func:`load_patterns` reads a caller file
  in the same shape, so adding a pattern needs no code change (Section 9.10);
* *reporting only* — findings warn and inform; they never block or edit
  (blocking is WP-2.6 / the rules block's decision).
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from ..api_errors import ErrorCode
from .diff import MergeBaseDiff
from .errors import GitHelperError

__all__ = [
    "DEFAULT_PATTERNS_PATH",
    "SecretFinding",
    "SecretPattern",
    "SecretScanResult",
    "load_patterns",
    "scan_patch",
]

#: The shipped default pattern set (Section 9.10 — documented defaults).
DEFAULT_PATTERNS_PATH: Final = Path(__file__).parent / "secret_patterns.toml"

_HUNK_HEADER: Final = re.compile(
    r"\A@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<start>\d+)(?:,(?P<count>\d+))? @@"
)
#: Clip for the surviving (non-matched) context around a redaction.
_EXCERPT_RADIUS: Final = 40


@dataclass(frozen=True, slots=True)
class SecretPattern:
    """One configurable secret-like pattern (TOML ``[[patterns]]`` row)."""

    id: str
    severity: str
    description: str
    compiled: re.Pattern[str]

    @property
    def regex(self) -> str:
        return self.compiled.pattern


@dataclass(frozen=True, slots=True)
class SecretFinding:
    """One redacted finding: where, what pattern, and safe context."""

    pattern_id: str
    severity: str
    path: str
    line: int
    excerpt: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "severity": self.severity,
            "path": self.path,
            "line": self.line,
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True, slots=True)
class SecretScanResult:
    """Summary plus per-file findings — the R5-corroboration shape."""

    findings: tuple[SecretFinding, ...]
    files_scanned: int
    lines_scanned: int

    @property
    def count(self) -> int:
        return len(self.findings)

    @property
    def by_file(self) -> dict[str, tuple[SecretFinding, ...]]:
        grouped: dict[str, list[SecretFinding]] = {}
        for finding in self.findings:
            grouped.setdefault(finding.path, []).append(finding)
        return {path: tuple(entries) for path, entries in grouped.items()}

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "files_scanned": self.files_scanned,
            "lines_scanned": self.lines_scanned,
            "findings": [finding.as_dict() for finding in self.findings],
        }


def load_patterns(path: Path | None = None) -> tuple[SecretPattern, ...]:
    """Read a pattern TOML file (defaults to the shipped set).

    The file holds ``[[patterns]]`` rows with ``id``, ``severity``,
    ``description`` and ``regex``. Invalid files raise ``VALIDATION_ERROR``
    with the offending row — a broken pattern set must fail loudly, never
    silently scan less.
    """
    source = Path(path) if path is not None else DEFAULT_PATTERNS_PATH
    try:
        raw = tomllib.loads(source.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"could not read secret-scan patterns from {str(source)!r} ({type(exc).__name__}).",
            hint="the pattern set is configuration (Section 9.10): a TOML file "
            "with [[patterns]] rows carrying id/severity/description/regex.",
            next_action="Fix or restore the pattern file; the scanner never "
            "falls back to a smaller set silently.",
            details={"path": str(source)},
        ) from exc

    patterns: list[SecretPattern] = []
    for index, row in enumerate(raw.get("patterns", [])):
        if not isinstance(row, dict):
            raise _bad_pattern(source, index, "row is not a table")
        missing = [key for key in ("id", "severity", "description", "regex") if key not in row]
        if missing:
            raise _bad_pattern(source, index, f"missing keys: {', '.join(missing)}")
        severity = str(row["severity"])
        if severity not in {"high", "medium"}:
            raise _bad_pattern(source, index, f"severity must be high|medium, got {severity!r}")
        try:
            compiled = re.compile(str(row["regex"]))
        except re.error as exc:
            raise _bad_pattern(source, index, f"invalid regex: {exc}") from exc
        patterns.append(
            SecretPattern(
                id=str(row["id"]),
                severity=severity,
                description=str(row["description"]),
                compiled=compiled,
            )
        )
    if not patterns:
        raise _bad_pattern(source, -1, "the file defines no [[patterns]] rows")
    return tuple(patterns)


def _bad_pattern(source: Path, index: int, reason: str) -> GitHelperError:
    return GitHelperError(
        ErrorCode.VALIDATION_ERROR,
        f"secret-scan pattern file {str(source)!r} is invalid at entry "
        f"{index if index >= 0 else 'n/a'}: {reason}.",
        hint="each [[patterns]] row needs id, severity (high|medium), "
        "description and a valid Python regex.",
        next_action="Correct the pattern file (Section 9.10 configuration) and retry.",
        details={"path": str(source), "entry": index, "reason": reason},
    )


def _redact(line: str, match: re.Match[str], pattern_id: str) -> str:
    """Replace the matched span; clip the surviving context to a radius.

    The matched material — the only secret the line provably contains —
    never survives; what remains is enough surrounding context for a human
    to locate the line (Section 12.4).
    """
    start, end = match.span()
    left = line[max(0, start - _EXCERPT_RADIUS) : start]
    right = line[end : end + _EXCERPT_RADIUS]
    ellipsis_left = "…" if start > _EXCERPT_RADIUS else ""
    ellipsis_right = "…" if end + _EXCERPT_RADIUS < len(line) else ""
    return f"{ellipsis_left}{left}[REDACTED:{pattern_id}]{right}{ellipsis_right}"


def _added_lines(patch: str) -> Iterable[tuple[str, int, str]]:
    """Yield ``(path, new_file_line_number, line_text)`` for ``+`` lines.

    File comes from ``+++ b/<path>`` headers; line numbers track the hunk
    headers' ``+start`` counters across ``+`` and context lines (removed and
    ``\\ No newline`` lines do not advance the new-file counter). Hunk bodies
    are tracked by their declared line counts, so an added line whose content
    itself starts with ``+++`` can never be mistaken for a file header.
    """
    path: str | None = None
    line_number: int | None = None
    remaining = 0  # lines left in the current hunk body
    for raw_line in patch.splitlines():
        if remaining == 0 and raw_line.startswith("+++ "):
            target = raw_line[4:].strip()
            prefix = "b/"
            path = target[len(prefix) :] if target.startswith(prefix) else target
            line_number = None
            continue
        hunk = _HUNK_HEADER.match(raw_line)
        if hunk is not None:
            # The hunk body holds old-side plus new-side lines (context,
            # added, removed); the new-file counter advances on the new side.
            old_count = hunk.group("old_count")
            new_count = hunk.group("count")
            remaining = (int(old_count) if old_count is not None else 1) + (
                int(new_count) if new_count is not None else 1
            )
            line_number = int(hunk.group("start"))
            continue
        if path is None or line_number is None:
            continue
        if raw_line.startswith("+"):
            yield path, line_number, raw_line[1:]
            line_number += 1
            remaining -= 1
        elif raw_line.startswith(" "):
            line_number += 1
            remaining -= 1
        elif raw_line.startswith("-"):
            remaining -= 1
        # '\ No newline at end of file' belongs to the hunk but is not a
        # content line — it does not consume a body line.
        elif raw_line.startswith("\\"):
            continue


def scan_patch(
    diff: MergeBaseDiff | str,
    *,
    patterns: Sequence[SecretPattern] | None = None,
    ignore_pattern_ids: Iterable[str] = (),
) -> SecretScanResult:
    """Scan the added lines of *diff* (a bundle or a raw unified patch).

    ``ignore_pattern_ids`` drops specific pattern ids narrowly (MT-2.10-04:
    configurable ignore rules, default none). Binary-file entries in a bundle
    contribute no lines — Git's own output defines the boundary.
    """
    patch = diff.patch if isinstance(diff, MergeBaseDiff) else diff
    active = tuple(patterns) if patterns is not None else load_patterns()
    ignored = frozenset(ignore_pattern_ids)

    findings: list[SecretFinding] = []
    files_scanned: set[str] = set()
    lines_scanned = 0
    for path, line_number, text in _added_lines(patch):
        files_scanned.add(path)
        lines_scanned += 1
        for pattern in active:
            if pattern.id in ignored:
                continue
            match = pattern.compiled.search(text)
            if match is None:
                continue
            findings.append(
                SecretFinding(
                    pattern_id=pattern.id,
                    severity=pattern.severity,
                    path=path,
                    line=line_number,
                    excerpt=_redact(text, match, pattern.id),
                )
            )
    return SecretScanResult(
        findings=tuple(findings),
        files_scanned=len(files_scanned),
        lines_scanned=lines_scanned,
    )
