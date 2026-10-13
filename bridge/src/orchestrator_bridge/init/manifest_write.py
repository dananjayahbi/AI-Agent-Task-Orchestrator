"""Manifest write duty of ``orchestrator init`` (FR-MCP-08 duty 1; Section 10.11; MT-2.12-01).

Responsibilities, in order:

* :func:`find_git_root` — the write target. Same ceiling rule as MT-2.2-01's
  discovery walk (``.git`` directory *or* worktree/submodule pointer file is
  the repository root); an exported tree without Git fails with a clear
  message because "at the repository root" would otherwise be a guess.
* :func:`fetch_project_inputs` — the backend is the source of truth for
  project identity (Section 19.3): the *project row* and its *policy row*
  (agent-readable for the token's own project, Section 9.2) supply the id,
  name, default branch, branch prefix and audit default. Nothing is derived
  client-side; an unreachable backend, a rejected credential or a wrong
  project each fail with a remedy-bearing :class:`InitError` (no-backend
  invocation fails loudly — init's remaining duties need the API anyway).
* :func:`compose_manifest` — pure projection into the shared schema's
  allowlisted keys (FR-SEC-04: no secret, no absolute path can fit), mirroring
  the backend renderer's ``{PID}`` branch-prefix resolution (G-09) and the
  Section 10.3 example's ``agent_hints``.
* :func:`write_manifest` — conformance-gated write at the root with an
  overwrite guard: an existing manifest is never clobbered without
  confirmation (``--force`` bypasses) and an identical document is left
  untouched ("re-run without rewriting when unchanged").

The written file is what MT-2.2-01 discovers and MT-2.2-02 validates — this
module round-trips every document through that same validator before a byte
hits disk (single schema, Section 19.6).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..endpoints import endpoint
from ..errors import INIT_COMMAND, InitError
from ..manifest_discovery import MANIFEST_FILENAME
from ..manifest_validation import validate_manifest
from ..scrub import scrub_text
from ..transport import ApiClient

__all__ = [
    "MANIFEST_SCHEMA_URL",
    "PID_PATTERN",
    "ProjectInputs",
    "WriteOutcome",
    "compose_manifest",
    "fetch_project_inputs",
    "find_git_root",
    "resolve_branch_prefix",
    "write_manifest",
]

#: Section 7.3 canonical project id shape (shared with the manifest schema).
PID_PATTERN: Final = re.compile(r"^PID[0-9]{5}$")

#: The Section 10.3 example's ``$schema`` URL, verbatim — the same value the
#: backend renderer ships (MT-1.3-05 recorded decision; the published file's
#: basename matches this path).
MANIFEST_SCHEMA_URL: Final = "https://orchestrator.local/schemas/manifest.v1.json"


class WriteOutcome(StrEnum):
    """What happened to the manifest file (unchanged runs skip the write)."""

    WRITTEN = "written"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class ProjectInputs:
    """Backend-verified fields the manifest projects (Section 19.3)."""

    project_id: str
    name: str
    default_branch: str
    branch_prefix: str  # policy prefix as stored — may still hold ``{PID}``
    audit_required_default: bool


def find_git_root(start: Path) -> Path:
    """Walk *start* upward to the Git root (MT-2.2-01's ceiling rule).

    ``.git`` as a directory (normal repository) or as a file (worktree /
    submodule pointer) both mark the root. No Git above *start* is an error:
    the manifest's one-per-repo rule needs a repository root to write at.
    """
    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            raise InitError(
                f"no Git repository found from {current} upward; "
                f"'{INIT_COMMAND}' writes orchestrator.json at the repository "
                "root, so run it inside a clone"
            )
        current = parent


def _read_field(payload: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in payload:
        raise InitError(
            f"the backend response from {where} has no {key!r} field — not the "
            "documented shape; check the endpoint and API version"
        )
    return payload[key]


def _project_error(pid: str, exc: ApiError) -> InitError:
    """Map one failed project read to a remedy-bearing init failure."""
    scrubbed = scrub_text(str(exc))
    if exc.code is ErrorCode.AUTH_FORBIDDEN_PROJECT:
        return InitError(
            f"the configured agent token is not valid for project {pid} "
            f"(backend code {ErrorCode.AUTH_FORBIDDEN_PROJECT}): one token is "
            "scoped to exactly one project (Section 10.3). Fix: use the token "
            f"issued for {pid}, or pass the project id the token belongs to"
        )
    if exc.code is ErrorCode.AUTH_REQUIRED:
        return InitError(
            f"the backend rejected the credential while verifying {pid} "
            f"(backend code {ErrorCode.AUTH_REQUIRED}). Fix: set "
            "ORCHESTRATOR_AGENT_TOKEN to a live agent token, or paste one at "
            f"the prompt, then re-run '{INIT_COMMAND}'"
        )
    if exc.code is ErrorCode.ROLE_NOT_PERMITTED:
        return InitError(
            f"the backend refused the project read for {pid} "
            f"(backend code {ErrorCode.ROLE_NOT_PERMITTED}): this credential "
            "cannot read projects. Fix: reissue an agent token for the "
            "project from the orchestrator UI"
        )
    if exc.kind is ErrorKind.TRANSPORT_FAILURE:
        return InitError(
            f"backend unreachable while verifying project {pid} ({scrubbed}); "
            "init's remaining steps need the API. Fix: start the backend (or "
            "correct --api / ORCHESTRATOR_API_BASE_URL) and re-run"
        )
    return InitError(
        f"cannot verify project {pid} against the backend ({scrubbed}). Fix: "
        "check the endpoint, the token and the project id, then re-run "
        f"'{INIT_COMMAND}'"
    )


def fetch_project_inputs(client: ApiClient, project_id: str) -> ProjectInputs:
    """Read the project and policy rows for *project_id* (Section 9.2 reads).

    Both calls are the bridge's existing catalog endpoints
    (``project_context`` / ``project_policy``): an agent token reads its own
    project (scope-guarded; a foreign project answers
    ``AUTH_FORBIDDEN_PROJECT``). The responses are *projected*, never
    reinterpreted — only the documented field types are accepted, anything
    else fails as a shape error rather than writing a guessed manifest.
    """
    if not PID_PATTERN.match(project_id):
        raise InitError(
            f"{project_id!r} is not a project id — expected PID followed by "
            "five digits (Section 7.3), e.g. --project-id PID00007"
        )
    try:
        project = client.request("GET", endpoint("project_context").path.format(pid=project_id))
        policy = client.request("GET", endpoint("project_policy").path.format(pid=project_id))
    except ApiError as exc:
        raise _project_error(project_id, exc) from None
    if not isinstance(project, Mapping) or not isinstance(policy, Mapping):
        raise InitError(
            f"the backend responses for {project_id} are not the documented "
            "objects; check the endpoint and API version"
        )

    name = _read_field(project, "name", "GET /projects/{pid}")
    default_branch = _read_field(project, "default_branch", "GET /projects/{pid}")
    branch_prefix = _read_field(policy, "branch_prefix", "GET /projects/{pid}/policy")
    audit_default = _read_field(policy, "audit_required_default", "GET /projects/{pid}/policy")
    if not all(
        isinstance(value, str) and value.strip() for value in (name, default_branch, branch_prefix)
    ):
        raise InitError(
            f"the backend responses for {project_id} carry a non-text "
            "name/branch/prefix field — not the documented shape"
        )
    if not isinstance(audit_default, bool):
        raise InitError(
            f"the backend policy for {project_id} has a non-boolean "
            "audit_required_default — not the documented shape"
        )
    return ProjectInputs(
        project_id=project_id,
        name=name,
        default_branch=default_branch,
        branch_prefix=branch_prefix,
        audit_required_default=audit_default,
    )


def resolve_branch_prefix(branch_prefix: str, project_id: str) -> str:
    """G-09: resolve the policy's ``{PID}`` token — the backend's own rule."""
    return branch_prefix.replace("{PID}", project_id)


def compose_manifest(inputs: ProjectInputs, *, orchestrator_api: str) -> dict[str, Any]:
    """Project the verified inputs into the Section 10.3 manifest document.

    Exactly the shared schema's allowlisted keys (``schemas/manifest.v1.json``
    is ``additionalProperties: false``); ``agent_hints`` carries the Section
    10.3 example's defaults, matching the backend renderer so both sources
    produce the same document. No timestamp: the schema has no such key, so
    the manifest stays hermetic and re-runs are byte-comparable.
    """
    return {
        "$schema": MANIFEST_SCHEMA_URL,
        "schema_version": 1,
        "project_id": inputs.project_id,
        "project_name": inputs.name,
        "orchestrator_api": orchestrator_api,
        "default_branch": inputs.default_branch,
        "auto_branch_prefix": resolve_branch_prefix(inputs.branch_prefix, inputs.project_id),
        "audit_required_default": inputs.audit_required_default,
        "agent_hints": {
            "test_command_default": "see task",
            "worktree_mode": False,
        },
    }


def write_manifest(
    root: Path,
    document: Mapping[str, Any],
    *,
    force: bool,
    confirm: Callable[[str], bool],
) -> WriteOutcome:
    """Validate then write *document* at ``root/orchestrator.json``.

    Pre-write validation runs the candidate through MT-2.2-02's shared
    validator, so writer/validator drift fails here rather than at the next
    bridge startup. An existing manifest is only replaced after ``confirm``
    says yes (``force`` skips the question); declining raises
    :class:`InitError` naming ``--force``. An existing document equal to the
    new one short-circuits to :attr:`WriteOutcome.UNCHANGED` — no write, no
    prompt (re-init is safe).
    """
    path = root / MANIFEST_FILENAME
    payload = dict(document)
    validate_manifest(payload, source=path)  # single schema, round-trip gate

    if path.is_file():
        try:
            current_text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise InitError(f"cannot read the existing {path}: {exc}") from None
        try:
            current_document: object = json.loads(current_text)
        except json.JSONDecodeError:
            current_document = None  # corrupt file counts as "different"
        if current_document == payload:
            return WriteOutcome.UNCHANGED
        question = f"{path} exists — replace it with the backend-verified manifest?"
        if not force and not confirm(question):
            raise InitError(
                f"refusing to overwrite {path} without confirmation; re-run "
                "with --force to replace it (or answer yes interactively)"
            )

    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(serialized, encoding="utf-8", newline="\n")
    return WriteOutcome.WRITTEN
