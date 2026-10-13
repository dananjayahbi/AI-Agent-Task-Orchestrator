"""MT-2.5-01 — the capability resolver's four-step order (Section 10.4).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.5-attachment-tool/
MT-2.5-01-capability-resolver.md (parent plan Sections 10.4, 10.9; ADR-006).
"""

from __future__ import annotations

from types import SimpleNamespace

from orchestrator_bridge.capabilities import (
    CAPABILITY_TEXT_ONLY,
    CAPABILITY_UNKNOWN,
    CAPABILITY_VISION,
    IMAGE_REQUEST_NOTE,
    CapabilityResolution,
    ResolutionStep,
    client_identity,
    resolve_capability,
)
from orchestrator_bridge.capability_table import CapabilityTable, ClientCapability


def _table(*entries: ClientCapability) -> CapabilityTable:
    return CapabilityTable(tuple(entries))


def test_explicit_format_short_circuits_the_step_report() -> None:
    resolution = resolve_capability("image_base64", session_capability="vision")
    assert resolution.step is ResolutionStep.EXPLICIT_FORMAT
    assert resolution.format_preference == "image_base64"
    assert resolution.capability == CAPABILITY_VISION  # still resolved for the gate


def test_explicit_format_wins_over_table_and_still_reports_capability() -> None:
    table = _table(ClientCapability(client_names=("known-vision",), capability=CAPABILITY_VISION))
    resolution = resolve_capability("markdown", client_name="known-vision", table=table)
    assert resolution.step is ResolutionStep.EXPLICIT_FORMAT
    assert resolution.capability == CAPABILITY_VISION


def test_session_capability_is_step_2_and_short_circuits_the_table() -> None:
    table = _table(ClientCapability(client_names=("known-vision",), capability=CAPABILITY_VISION))
    resolution = resolve_capability(
        session_capability=CAPABILITY_TEXT_ONLY, client_name="known-vision", table=table
    )
    assert resolution.step is ResolutionStep.SESSION_CONFIG
    assert resolution.capability == CAPABILITY_TEXT_ONLY
    assert resolution.note is None  # a decided capability needs no guidance


def test_client_table_lookup_is_step_3() -> None:
    table = _table(
        ClientCapability(client_names=("known-vision",), capability=CAPABILITY_VISION),
    )
    resolution = resolve_capability(client_name="Known-Vision", client_version="1.2.0", table=table)
    assert resolution.step is ResolutionStep.CLIENT_TABLE
    assert resolution.capability == CAPABILITY_VISION
    assert resolution.client == "Known-Vision 1.2.0"


def test_default_is_text_safe_with_the_explicit_request_note() -> None:
    resolution = resolve_capability()
    assert resolution.step is ResolutionStep.DEFAULT_TEXT_SAFE
    assert resolution.capability == CAPABILITY_UNKNOWN
    assert resolution.note == IMAGE_REQUEST_NOTE
    assert not resolution.vision


def test_unknown_capability_always_carries_the_how_to_request_note() -> None:
    resolution = resolve_capability("image_base64")
    assert resolution.step is ResolutionStep.EXPLICIT_FORMAT
    assert resolution.note is None  # the explicit format *is* the answer here
    auto = resolve_capability()
    assert auto.note == IMAGE_REQUEST_NOTE


def test_invalid_defensive_session_value_falls_to_the_default() -> None:
    resolution = resolve_capability(session_capability="pretend-vision")
    assert resolution.step is ResolutionStep.DEFAULT_TEXT_SAFE
    assert resolution.capability == CAPABILITY_UNKNOWN


def test_table_entry_recorded_unknown_is_an_explicit_step_3_answer() -> None:
    table = _table(
        ClientCapability(client_names=("unverified-client",), capability=CAPABILITY_UNKNOWN)
    )
    resolution = resolve_capability(client_name="unverified-client", table=table)
    assert resolution.step is ResolutionStep.CLIENT_TABLE
    assert resolution.capability == CAPABILITY_UNKNOWN
    assert resolution.note == IMAGE_REQUEST_NOTE


def test_client_identity_reads_the_mcp_handshake_shape() -> None:
    context = SimpleNamespace(
        session=SimpleNamespace(
            client_params=SimpleNamespace(
                client_info=SimpleNamespace(name="claude-code", version="2.0.1")
            )
        )
    )
    assert client_identity(context) == ("claude-code", "2.0.1")


def test_client_identity_is_none_safe_at_every_layer() -> None:
    assert client_identity(None) == (None, None)
    assert client_identity(SimpleNamespace()) == (None, None)
    assert client_identity(SimpleNamespace(session=SimpleNamespace(client_params=None))) == (
        None,
        None,
    )
    bare = SimpleNamespace(
        session=SimpleNamespace(
            client_params=SimpleNamespace(client_info=SimpleNamespace(name="  ", version=None))
        )
    )
    assert client_identity(bare) == (None, None)


def test_resolution_is_reported_in_the_structured_shape() -> None:
    resolution: CapabilityResolution = resolve_capability()
    assert {
        "capability": resolution.capability,
        "step": str(resolution.step.value),
        "client": resolution.client,
        "note": resolution.note,
    }["step"] == "default_text_safe"
