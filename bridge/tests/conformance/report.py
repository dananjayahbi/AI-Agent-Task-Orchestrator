"""Conformance report model (MT-2.11-01; Sections 10.8, 10.9, 18).

The runner's output is a machine-readable report whose four top-level columns
are exactly the client-compatibility matrix columns of Section 10.9 — one row
of ``docs/agent-guides/compatibility-matrix.md`` per client run — plus the
per-check pass/fail evidence the MT demands.

Status semantics:

``pass`` / ``fail``
    A conformance check; any ``fail`` makes the whole run fail (exit 1).
``skip``
    The check could not run (missing prerequisite, e.g. no attachment on the
    task); recorded with the reason, never counted as a pass.
``reported``
    A recorded fact that is explicitly *not* a pass/fail judgment — prompt
    absence is reported, not failed (MT-2.11-01 / NFR-08).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "CheckResult",
    "ConformanceReport",
    "MATRIX_COLUMNS",
    "Status",
]

Status = Literal["pass", "fail", "skip", "reported"]

#: Section 10.9 client-compatibility matrix columns, verbatim.
MATRIX_COLUMNS: tuple[str, str, str, str] = (
    "Transport",
    "Prompts surfaced",
    "Images in tool results",
    "Notes",
)


@dataclass
class CheckResult:
    """One per-check verdict (id, role, status, human-readable detail)."""

    id: str
    role: str
    status: Status
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "role": self.role, "status": self.status, "detail": self.detail}


@dataclass
class ConformanceReport:
    """A finished run: matrix columns + every check + observed error codes."""

    client_label: str
    transport: str
    bridge_version: str = ""
    protocol_version: str = ""
    notes: list[str] = field(default_factory=list)
    prompts_surfaced: list[str] = field(default_factory=list)
    prompts_absent: list[str] = field(default_factory=list)
    prompt_render_failures: list[str] = field(default_factory=list)
    tools_exercised: list[str] = field(default_factory=list)
    observed_error_codes: list[str] = field(default_factory=list)
    vision_path_seen: bool = False
    text_only_path_seen: bool = False
    attachment_skipped: bool = False
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, check: CheckResult) -> CheckResult:
        self.checks.append(check)
        return check

    @property
    def failures(self) -> list[CheckResult]:
        return [check for check in self.checks if check.status == "fail"]

    @property
    def skipped(self) -> list[CheckResult]:
        return [check for check in self.checks if check.status == "skip"]

    @property
    def passed(self) -> bool:
        """Exit-code contract: no failed check → 0; any failure → 1."""
        return not self.failures

    def note_tools(self, name: str) -> None:
        """Record that a Section 10.5 tool was exercised by this run."""
        if name not in self.tools_exercised:
            self.tools_exercised.append(name)

    def note_error_code(self, code: str | None) -> None:
        """Record an observed Section 9.2 code for the catalog-membership check."""
        if code is not None and code not in self.observed_error_codes:
            self.observed_error_codes.append(code)

    def images_column(self) -> str:
        """The Section 10.9 "Images in tool results" cell for this run."""
        if self.vision_path_seen:
            return "yes — image content blocks observed in read_task_attachment"
        if self.text_only_path_seen:
            return "no — text-only path: OCR + description with untrusted banner"
        if self.attachment_skipped:
            return "not exercised — no attachment on the seeded task"
        return "not exercised"

    def prompts_column(self) -> str:
        """The Section 10.9 "Prompts surfaced" cell for this run."""
        if self.prompts_surfaced and not self.prompts_absent:
            return f"yes — {len(self.prompts_surfaced)} of 4"
        if self.prompts_surfaced:
            return (
                f"partial — {len(self.prompts_surfaced)} of 4 ({', '.join(self.prompts_surfaced)})"
            )
        return "no"

    def matrix_row(self) -> dict[str, str]:
        """The four Section 10.9 cells this run fills in for its client row."""
        notes = "; ".join(self.notes) if self.notes else "—"
        if self.failures:
            notes = (
                f"{len(self.failures)} failed check(s): "
                + ", ".join(check.id for check in self.failures)
                + f" — {notes}"
            )
        return {
            "Transport": "STDIO" if self.transport == "stdio" else "HTTP/SSE",
            "Prompts surfaced": self.prompts_column(),
            "Images in tool results": self.images_column(),
            "Notes": notes,
        }

    def as_dict(self) -> dict[str, Any]:
        """The JSON report artifact the runner writes (``--report``)."""
        return {
            "matrix": self.matrix_row(),
            "client": self.client_label,
            "transport": self.transport,
            "bridge_version": self.bridge_version,
            "protocol_version": self.protocol_version,
            "prompts_surfaced": self.prompts_surfaced,
            "prompts_absent": self.prompts_absent,
            "tools_exercised": self.tools_exercised,
            "observed_error_codes": self.observed_error_codes,
            "passed": self.passed,
            "checks": [check.as_dict() for check in self.checks],
            "notes": self.notes,
        }

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(self.as_dict(), indent=2) + "\n", encoding="utf-8")

    def summary(self) -> str:
        """Human-readable stdout summary of a run."""
        lines = [
            f"conformance report — {self.client_label} ({self.transport})",
            f"  result: {'PASS' if self.passed else 'FAIL'} "
            f"({len(self.checks)} checks, {len(self.failures)} failed, "
            f"{len(self.skipped)} skipped)",
            f"  tools exercised: {len(self.tools_exercised)}/10",
            "  Section 10.9 matrix row:",
        ]
        for column in MATRIX_COLUMNS:
            lines.append(f"    {column}: {self.matrix_row()[column]}")
        for check in self.checks:
            lines.append(f"    [{check.status:>8}] {check.id} — {check.detail}")
        return "\n".join(lines)
