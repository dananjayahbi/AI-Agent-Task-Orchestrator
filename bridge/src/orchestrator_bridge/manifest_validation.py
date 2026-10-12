"""Manifest schema and version validation (parent plan Section 10.3 step 2; MT-2.2-02).

Two discrete, deliberately distinguishable checks that run immediately after
discovery and *before* any token or session work (FR-SEC-01 hygiene — an invalid
manifest never gets near a credential):

1. **Version compatibility** — the declared integer ``schema_version`` must be in
   :data:`SUPPORTED_SCHEMA_VERSIONS`, checked as its own step so an unsupported
   version raises :class:`ManifestVersionError` ("upgrade the bridge") and never
   a structural message. The plan leaves version-range semantics unstated
   (MT-2.2-02 risk note); the rule fixed here is **integer generation, exact
   match**: the schema file itself is versioned (``manifest.v1.json``), versions
   are not semver, and a future generation fails closed rather than guessing
   forward compatibility. The full client-backend contract-versioning scheme
   stays Appendix B's B-01 fast-follow ADR, which supersedes this rule; the
   Section 10.11 *API version header* check is a backend HTTP exchange and joins
   with WP-2.3 (no canonical header name exists yet).
2. **Structural validation** against the published schema
   ``schemas/manifest.v1.json`` — the single source shared with the backend's
   manifest renderer (MT-1.3-05) and WP-2.12's writer (Section 19.6; one schema,
   two consumers). The schema is loaded from disk at runtime and never fetched
   over the network (MT-2.2-02 out of scope): repository checkouts read the
   canonical ``schemas/`` file; an installed wheel reads the copy the build
   force-includes from that same file (see ``bridge/pyproject.toml``), so a
   schema diff is one reviewed change (Section 20.4 item 4).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, best_match

from .errors import INIT_COMMAND, ManifestValidationError, ManifestVersionError
from .scrub import scrub_text

__all__ = [
    "SUPPORTED_SCHEMA_VERSIONS",
    "load_manifest_schema",
    "manifest_schema_path",
    "validate_manifest",
]

#: Manifest generations this bridge understands — exact-match rule (module docstring).
SUPPORTED_SCHEMA_VERSIONS: Final[frozenset[int]] = frozenset({1})

_PACKAGE_DIR = Path(__file__).resolve().parent
#: Source checkout: bridge/src/orchestrator_bridge → repo root holding schemas/.
_REPO_ROOT = _PACKAGE_DIR.parents[2]
_SCHEMA_RELPATH = Path("schemas") / "manifest.v1.json"
#: Wheel copy, force-included from the canonical file by the build.
_PACKAGED_SCHEMA = _PACKAGE_DIR / "schemas" / "manifest.v1.json"


def manifest_schema_path() -> Path:
    """The published schema file — canonical repo file first, packaged copy next.

    Raises :class:`ManifestValidationError` when neither exists (broken install);
    never downloads (Section 10.3 "published schema" = shipped with the bridge).
    """
    if (_REPO_ROOT / _SCHEMA_RELPATH).is_file():
        return _REPO_ROOT / _SCHEMA_RELPATH
    if _PACKAGED_SCHEMA.is_file():
        return _PACKAGED_SCHEMA
    raise ManifestValidationError(
        f"published manifest schema not found (looked in {_REPO_ROOT / _SCHEMA_RELPATH} "
        f"and {_PACKAGED_SCHEMA}); reinstall the bridge or run it from a checkout"
    )


def load_manifest_schema() -> dict[str, Any]:
    """Read and meta-schema-check the published schema (once per validation call)."""
    path = manifest_schema_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(f"cannot load published schema {path}: {exc}") from None
    if not isinstance(raw, dict):
        raise ManifestValidationError(f"published schema {path} is not a JSON object")
    try:
        Draft202012Validator.check_schema(raw)
    except Exception as exc:  # jsonschema.SchemaError — the published file itself is broken
        raise ManifestValidationError(f"published schema {path} is invalid: {exc}") from None
    return raw


def _instance_location(error: ValidationError) -> str:
    """``$.field[0].nested``-style pointer for the failing instance location."""
    parts = ["$"]
    for part in error.absolute_path:
        parts.append(f"[{part}]" if isinstance(part, int) else f".{part}")
    return "".join(parts)


def _format_error(error: ValidationError) -> str:
    # scrub_text is defense in depth: schema messages may echo instance values,
    # and this string reaches both the log and stderr (single redaction point).
    return scrub_text(f"{_instance_location(error)}: {error.message}")


def validate_manifest(document: object, *, source: Path | None = None) -> dict[str, Any]:
    """Validate *document* per Section 10.3 step 2; return it as a mapping on success.

    Order: JSON object precondition → discrete version check → full schema
    validation. Raises :class:`ManifestVersionError` for an unsupported
    ``schema_version`` and :class:`ManifestValidationError` for anything else
    malformed — the two messages are intentionally distinguishable so users know
    whether to fix the file or upgrade the bridge (MT-2.2-02 acceptance).
    *source* is the manifest path, added to messages for context.
    """
    label = f"manifest {source}" if source is not None else "manifest"
    if not isinstance(document, dict):
        raise ManifestValidationError(
            f"{label} must contain a JSON object, got {type(document).__name__}"
        )

    version = document.get("schema_version")
    # bool is an int subclass in Python but never a valid schema_version.
    if isinstance(version, int) and not isinstance(version, bool):
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            supported = ", ".join(str(item) for item in sorted(SUPPORTED_SCHEMA_VERSIONS))
            raise ManifestVersionError(
                f"{label} declares unsupported schema_version {version} "
                f"(this bridge supports {supported}); upgrade the bridge or "
                f"regenerate the manifest with '{INIT_COMMAND}'"
            )
    # Non-integer/absent versions fall through: the schema reports the precise
    # structural fault (malformed file, not unsupported version).

    validator = Draft202012Validator(load_manifest_schema())
    error = best_match(validator.iter_errors(document))
    if error is not None:
        raise ManifestValidationError(f"{label} failed schema validation: {_format_error(error)}")
    return document
