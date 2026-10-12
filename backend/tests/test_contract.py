"""Contract tests for the generated OpenAPI document (MT-1.1-04; NFR-11).

The committed snapshot under ``schemas/openapi.yaml`` is the drift-gated
artifact in CI; these tests assert the *semantic* obligations the snapshot
alone cannot enforce:

* the Section 9.2 error envelope exists as ONE reusable component wrapping
  exactly the five documented fields under ``error``, and every non-2xx
  response references it (MT-0.5-02's reusable-schema obligation);
* every error code shown in the document exists in the Section 9.2 catalog
  (Section 20.4 item 5);
* every ``$ref`` in the document resolves (the contract is self-consistent);
* list endpoints follow the cursor shape of
  ``docs/plan/conventions/pagination.md`` (MT-0.5-04) — vacuous today because
  no list endpoint exists yet; the first one added (WP-1.2+) must satisfy it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from drf_spectacular.generators import SchemaGenerator

from apps.core.errors import CANONICAL_ERROR_CODES

_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    """The document as the backend generates it (no server, no snapshot I/O)."""
    generated = SchemaGenerator().get_schema(  # type: ignore[no-untyped-call]
        request=None, public=True
    )
    assert generated is not None, "schema generation produced no document"
    return cast(dict[str, Any], generated)


def _operations(schema: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, item in schema["paths"].items():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method in _METHODS and isinstance(operation, dict):
                yield path, method, operation


def _resolve(schema: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """Follow a one-level ``$ref`` into ``components/schemas`` (else identity)."""
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        component: dict[str, Any] = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]
        return component
    return node


def _json_response_schema(
    schema: dict[str, Any], operation: dict[str, Any], status_code: str
) -> dict[str, Any] | None:
    response = operation.get("responses", {}).get(status_code)
    if not isinstance(response, dict):
        return None
    content = response.get("content", {})
    document_schema = (content.get("application/json") or {}).get("schema")
    if not isinstance(document_schema, dict):
        return None
    return _resolve(schema, document_schema)


def test_document_contains_the_served_ops_routes(schema: dict[str, Any]) -> None:
    """Health routes are part of the contract (MT-1.1-03 scope of this doc)."""
    assert "/health/live" in schema["paths"]
    assert "/health/ready" in schema["paths"]


def test_error_envelope_is_one_reusable_component_with_five_fields(
    schema: dict[str, Any],
) -> None:
    """Section 9.2 envelope as a reusable schema (MT-0.5-02 obligation).

    The wire body is the five fields nested under ``error``; the component
    must model that wrapper exactly (the flat top-level schema was a contract
    bug, fixed at the Wave 2 gate).
    """
    envelope = schema["components"]["schemas"]["ErrorEnvelope"]
    assert set(envelope["properties"]) == {"error"}, "wrapper has one key: error"
    assert set(envelope.get("required", [])) == {"error"}
    body = _resolve(schema, envelope["properties"]["error"])
    assert set(body["properties"]) == {
        "code",
        "message",
        "retryable",
        "details",
        "correlation_id",
    }
    required = set(body.get("required", []))
    assert required == {"code", "message", "retryable", "correlation_id"}
    assert "details" not in required  # the remaining optional field


def test_every_non_2xx_response_references_the_error_envelope(
    schema: dict[str, Any],
) -> None:
    """Declared error responses use the shared component, not a local shape."""
    seen_2xx_responses = 0
    for path, method, operation in _operations(schema):
        for status_code, response in operation.get("responses", {}).items():
            if not status_code.startswith(("4", "5")):
                continue
            if not isinstance(response, dict):
                continue
            document_schema = (
                (response.get("content", {}) or {}).get("application/json", {}).get("schema")
            )
            assert isinstance(document_schema, dict), (
                f"{method.upper()} {path} {status_code}: error response has no schema"
            )
            ref = document_schema.get("$ref")
            assert isinstance(ref, str) and ref.endswith("/ErrorEnvelope"), (
                f"{method.upper()} {path} {status_code}: must reference the shared "
                f"ErrorEnvelope component, got {ref!r}"
            )
            seen_2xx_responses += 1
    assert seen_2xx_responses >= 1, "expected at least one documented error response"


def test_error_codes_in_the_document_exist_in_the_catalog(
    schema: dict[str, Any],
) -> None:
    """Section 20.4 item 5 — document codes are a subset of the 9.2 catalog."""
    envelope = schema["components"]["schemas"]["ErrorEnvelope"]
    body = _resolve(schema, envelope["properties"]["error"])
    code_node = body["properties"]["code"]
    code_schema = _resolve(schema, code_node)  # may be a $ref to the enum component
    documented = set(code_schema["enum"])
    assert documented, "error code enum must not be empty"
    outside_catalog = sorted(documented - set(CANONICAL_ERROR_CODES))
    assert not outside_catalog, f"document references codes outside the catalog: {outside_catalog}"


def test_every_ref_in_the_document_resolves(schema: dict[str, Any]) -> None:
    """NFR-11 self-consistency: no dangling component references."""

    def walk(node: Any, where: str) -> Iterator[tuple[str, str]]:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                yield where, ref
            for key, value in node.items():
                yield from walk(value, f"{where}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from walk(value, f"{where}/{index}")

    for where, ref in walk(schema, "#"):
        assert ref.startswith("#/"), f"{where}: external ref not allowed: {ref}"
        target: Any = schema
        for part in ref[2:].split("/"):
            assert isinstance(target, dict) and part in target, f"{where}: dangling ref {ref}"
            target = target[part]


def test_list_endpoints_follow_the_cursor_pagination_convention(
    schema: dict[str, Any],
) -> None:
    """MT-0.5-04 shape for every list endpoint; vacuous until WP-1.2 adds one.

    A list endpoint is recognised by its ``results``-bearing 200 object — the
    canonical two-member envelope. The first list endpoint added must satisfy
    this test; extend it together with the endpoint, never bypass it.
    """
    for path, method, operation in _operations(schema):
        if method != "get":
            continue
        response_schema = _json_response_schema(schema, operation, "200")
        if response_schema is None:
            continue
        properties = response_schema.get("properties") or {}
        if "results" not in properties:
            continue  # not a list endpoint
        assert response_schema.get("type") == "object", f"{path}: envelope is an object"
        assert set(properties) == {"results", "next_cursor"}, (
            f"{method.upper()} {path}: cursor envelope must be exactly "
            f"results + next_cursor (pagination.md)"
        )
        parameters = list(operation.get("parameters", [])) + list(
            schema["paths"][path].get("parameters", [])
        )
        query_names = {
            parameter["name"]
            for parameter in parameters
            if isinstance(parameter, dict) and parameter.get("in") == "query"
        }
        assert {"cursor", "page_size"} <= query_names, (
            f"{method.upper()} {path}: list endpoints declare the canonical "
            f"cursor and page_size parameters (pagination.md)"
        )
