"""MT-2.2-02 — manifest schema validation and version compatibility check.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.2-manifest-binding/
MT-2.2-02-schema-version-validation.md (parent plan Sections 10.3 step 2,
10.11, 19.1, 19.6; FR-MCP-02, FR-SEC-01).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from orchestrator_bridge.errors import (
    INIT_COMMAND,
    ManifestValidationError,
    ManifestVersionError,
)
from orchestrator_bridge.manifest_validation import (
    SUPPORTED_SCHEMA_VERSIONS,
    load_manifest_schema,
    manifest_schema_path,
    validate_manifest,
)

REPO_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "manifest.v1.json"


# --- the published schema: one source, meta-schema checked --------------------


def test_repo_schema_file_is_the_load_source() -> None:
    """Section 19.6 / Section 20.4 item 4: the checkout reads the canonical file."""
    assert manifest_schema_path() == REPO_SCHEMA
    assert REPO_SCHEMA.is_file()


def test_published_schema_is_a_valid_draft_2020_12_schema() -> None:
    schema = load_manifest_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)  # never raises for a healthy file


def test_missing_schema_file_fails_with_reinstall_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import orchestrator_bridge.manifest_validation as module

    monkeypatch.setattr(module, "_REPO_ROOT", tmp_path / "no-such-repo")
    monkeypatch.setattr(module, "_PACKAGED_SCHEMA", tmp_path / "no-such-packaged.json")
    with pytest.raises(ManifestValidationError, match="reinstall the bridge"):
        manifest_schema_path()


def test_packaged_copy_is_used_when_repo_file_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Installed wheel: the force-included copy becomes the published source."""
    import orchestrator_bridge.manifest_validation as module

    packaged = tmp_path / "site-packages" / "orchestrator_bridge" / "schemas" / "manifest.v1.json"
    packaged.parent.mkdir(parents=True)
    packaged.write_text(REPO_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(module, "_REPO_ROOT", tmp_path / "no-such-repo")
    monkeypatch.setattr(module, "_PACKAGED_SCHEMA", packaged)

    assert manifest_schema_path() == packaged
    assert load_manifest_schema() == json.loads(REPO_SCHEMA.read_text(encoding="utf-8"))


# --- valid documents pass (hand-written fixture + Section 10.3 example) -------


def test_minimal_known_good_manifest_passes(minimal_manifest: dict[str, object]) -> None:
    result = validate_manifest(minimal_manifest)
    assert result == minimal_manifest  # returned as-is: no derived fields (Section 19.3)


def test_plan_section_10_3_example_passes() -> None:
    """The hand-written plan example — independent of any writer (MT risk note)."""
    example = {
        "$schema": "https://orchestrator.local/schemas/manifest.v1.json",
        "schema_version": 1,
        "project_id": "PID00007",
        "project_name": "Tea Factory ERP",
        "orchestrator_api": "http://localhost:8000/api/v1",
        "default_branch": "main",
        "auto_branch_prefix": "feat/PID00007-",
        "audit_required_default": True,
        "agent_hints": {"test_command_default": "see task", "worktree_mode": False},
    }
    assert validate_manifest(example) == example


# --- structural faults: "fix the file" ---------------------------------------


def test_missing_required_field_raises_validation_error(
    minimal_manifest: dict[str, object],
) -> None:
    del minimal_manifest["project_id"]
    with pytest.raises(ManifestValidationError) as excinfo:
        validate_manifest(minimal_manifest)
    assert "project_id" in str(excinfo.value)


def test_wrong_type_raises_validation_error(minimal_manifest: dict[str, object]) -> None:
    minimal_manifest["audit_required_default"] = "yes"  # schema: boolean
    with pytest.raises(ManifestValidationError) as excinfo:
        validate_manifest(minimal_manifest)
    assert "audit_required_default" in str(excinfo.value)


def test_unknown_property_rejected_by_allowlist(minimal_manifest: dict[str, object]) -> None:
    """FR-SEC-04: ``additionalProperties: false`` — nothing beyond the allowlist."""
    minimal_manifest["surprise_key"] = True
    with pytest.raises(ManifestValidationError, match="surprise_key"):
        validate_manifest(minimal_manifest)


def test_smuggled_token_field_is_rejected_and_never_echoed(
    minimal_manifest: dict[str, object],
) -> None:
    """A bad manifest cannot introduce a credential: the key is rejected (MT-2.2-03
    belt-and-braces) and its value never reaches the error message."""
    minimal_manifest["agent_token"] = "planted-value-should-not-leak"
    with pytest.raises(ManifestValidationError) as excinfo:
        validate_manifest(minimal_manifest, source=Path("orchestrator.json"))
    message = str(excinfo.value)
    assert "agent_token" in message
    assert "planted-value-should-not-leak" not in message


def test_non_object_document_raises_validation_error() -> None:
    documents: list[object] = [[], "orchestrator.json", 7, None]
    for document in documents:
        with pytest.raises(ManifestValidationError, match="JSON object"):
            validate_manifest(document)


def test_source_path_appears_in_error_message(
    minimal_manifest: dict[str, object], tmp_path: Path
) -> None:
    minimal_manifest["project_name"] = ""
    with pytest.raises(ManifestValidationError) as excinfo:
        validate_manifest(minimal_manifest, source=tmp_path / "orchestrator.json")
    assert "orchestrator.json" in str(excinfo.value)


# --- version compatibility: a discrete, distinguishable step ------------------


def test_unsupported_version_raises_version_error_not_validation_error(
    minimal_manifest: dict[str, object],
) -> None:
    minimal_manifest["schema_version"] = 2
    with pytest.raises(ManifestVersionError) as excinfo:
        validate_manifest(minimal_manifest)
    message = str(excinfo.value)
    assert "unsupported schema_version 2" in message
    assert "upgrade the bridge" in message
    assert INIT_COMMAND in message
    # Distinguishable: the "fix the file" wording never appears (MT acceptance).
    assert "schema validation" not in message


def test_version_error_wins_over_structural_faults(
    minimal_manifest: dict[str, object],
) -> None:
    """The version check is its own step and runs before schema validation —
    an unsupported version reports "upgrade", not "fix the file"."""
    minimal_manifest["schema_version"] = 2
    del minimal_manifest["project_name"]  # also structurally broken
    with pytest.raises(ManifestVersionError, match="upgrade the bridge"):
        validate_manifest(minimal_manifest)


def test_supported_version_set_is_exact_match_integer_generation() -> None:
    """Version rule fixed in the WP changelog: integer generation, exact match
    (Appendix B B-01 supersedes when its ADR lands)."""
    assert SUPPORTED_SCHEMA_VERSIONS == frozenset({1})


def test_malformed_version_falls_through_to_schema_not_version_error(
    minimal_manifest: dict[str, object],
) -> None:
    """Non-integer/absent versions are structural faults: the schema names the
    precise problem instead of guessing a compatibility verdict. (``1.0`` is
    deliberately absent: JSON Schema defines it as the integer 1, so it passes.)"""
    for bad_version in ("1", None, True):
        document = dict(minimal_manifest)
        if bad_version is None:
            document.pop("schema_version")
        else:
            document["schema_version"] = bad_version
        with pytest.raises(ManifestValidationError) as excinfo:
            validate_manifest(document)
        assert not isinstance(excinfo.value, ManifestVersionError)


def test_bool_true_is_not_treated_as_supported_version(
    minimal_manifest: dict[str, object],
) -> None:
    """Python quirk guard: ``True == 1`` but a boolean is never schema_version 1."""
    minimal_manifest["schema_version"] = True
    with pytest.raises(ManifestValidationError):
        validate_manifest(minimal_manifest)


# --- error messages: one clear, scrubbed line --------------------------------


def test_validation_message_is_scrubbed(minimal_manifest: dict[str, object]) -> None:
    """Schema messages may echo instance values; the string reaches log and
    stderr, so it passes the single redaction point (Section 17)."""
    minimal_manifest["project_id"] = "token=super-secret-value"
    with pytest.raises(ManifestValidationError) as excinfo:
        validate_manifest(minimal_manifest)
    message = str(excinfo.value)
    assert "super-secret-value" not in message
    assert "[REDACTED]" in message
