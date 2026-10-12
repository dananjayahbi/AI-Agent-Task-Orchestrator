"""MT-2.3-05 — contract test: bridge client behavior vs `schemas/openapi.yaml`.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.3-api-client/
MT-2.3-05-openapi-contract-test.md (parent plan Sections 9.2, 10.11, 18, 20.4,
20.5; NFR-11; ADR-005).

Discipline:

* **Read-only** — the ADR-005 document is loaded and asserted against; never
  written (file protocol: `schemas/` belongs to the backend pipeline).
* **Fail loudly, never skip** — a missing/corrupt document fails every test
  that needs it with an explicit "schema missing" message (risk note), and a
  client/schema disagreement fails with a message naming the endpoint *and*
  the field (AC 4).
* **Mocked boundary, real client** — representative requests are built by
  `ApiClient` against an injected send seam (no live backend, no Docker),
  so headers under test are the ones actually sent.
* **Required structure, not exhaustive fields** — samples validate against
  the referenced component schemas (OpenAPI `nullable` translated for JSON
  Schema); optional-field drift does not fail the suite.
* **Pending endpoints** — `endpoints.PENDING_BACKEND` records which backend
  work package has yet to land an endpoint; absent-but-pending passes today,
  the moment the endpoint appears it is validated automatically, and any
  non-pending absence fails by name.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
import yaml
from jsonschema import Draft202012Validator

from orchestrator_bridge.api_errors import CANONICAL_ERROR_CODES, ApiError, ErrorCode
from orchestrator_bridge.config import load_settings
from orchestrator_bridge.correlation import CORRELATION_HEADER
from orchestrator_bridge.endpoints import BRIDGE_ENDPOINTS, PENDING_BACKEND, Endpoint
from orchestrator_bridge.transport import (
    API_VERSION_HEADER,
    EXPECTED_API_VERSION,
    ApiClient,
    WireResponse,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "schemas" / "openapi.yaml"
ABSENT_CONFIG = Path("no-such-bridge-config.toml")
TOKEN = "fixture-token-not-a-real-secret"


# --- loading: fail loudly, never skip ----------------------------------------


def load_openapi(path: Path) -> dict[str, Any]:
    """Load the ADR-005 document; raise with a clear message when it is unusable."""
    if not path.exists():
        raise AssertionError(
            f"OpenAPI document missing at {path} — the contract the bridge speaks "
            "is gone; drift protection must not evaporate silently (MT-2.3-05)"
        )
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AssertionError(f"{path} is not parseable YAML: {exc}") from None
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        raise AssertionError(f"{path} parsed but is not an OpenAPI document with paths")
    return document


@pytest.fixture(scope="module")
def openapi() -> dict[str, Any]:
    return load_openapi(OPENAPI_PATH)


# --- OpenAPI 3.0 → JSON Schema validation helpers ----------------------------


def _to_json_schema(node: Any) -> Any:
    """Deep-copy with refs localized and OpenAPI ``nullable`` translated.

    OpenAPI 3.0 writes ``type: string, nullable: true``; JSON Schema wants
    ``type: ["string", "null"]``. Unknown OpenAPI keywords are left as-is —
    the validator ignores them (risk note: assert required structure only).
    """
    if isinstance(node, list):
        return [_to_json_schema(item) for item in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key == "$ref" and isinstance(value, str) and value.startswith("#/components/schemas/"):
            out[key] = "#/$defs/" + value.rsplit("/", 1)[-1]
        else:
            out[key] = _to_json_schema(value)
    if out.get("nullable") is True:
        declared = out.get("type")
        if isinstance(declared, str):
            out["type"] = [declared, "null"]
        del out["nullable"]
    return out


def _component_schema(component: str, document: dict[str, Any]) -> dict[str, Any]:
    schemas = document.get("components", {}).get("schemas", {})
    if component not in schemas:
        raise AssertionError(
            f"components.schemas.{component} missing from {OPENAPI_PATH} "
            "— the document drifted from the error conventions (error-envelope.md)"
        )
    defs = {name: _to_json_schema(schema) for name, schema in schemas.items()}
    return {"$defs": defs, "$ref": f"#/$defs/{component}"}


def assert_contract(instance: Any, component: str, *, where: str, document: dict[str, Any]) -> None:
    """Validate *instance* against a component schema; failure names where + field."""
    validator = Draft202012Validator(_component_schema(component, document))
    errors = sorted(validator.iter_errors(instance), key=lambda err: str(list(err.path)))
    if errors:
        first = errors[0]
        field = ".".join(str(part) for part in first.path) or "<root>"
        raise AssertionError(
            f"contract mismatch for {where}: field '{field}' violates "
            f"components.schemas.{component}: {first.message}"
        )


def _operation(document: dict[str, Any], endpoint: Endpoint) -> dict[str, Any] | None:
    item = document["paths"].get(endpoint.path)
    if not isinstance(item, dict):
        return None
    operation = item.get(endpoint.method.lower())
    return operation if isinstance(operation, dict) else None


def _assert_resolved(document: dict[str, Any], endpoint: Endpoint) -> dict[str, Any] | None:
    """Operation for *endpoint*, or ``None`` while its backend WP is pending."""
    operation = _operation(document, endpoint)
    where = f"{endpoint.method} {endpoint.path}"
    if operation is None:
        pending = PENDING_BACKEND.get(endpoint.id)
        if pending is None:
            raise AssertionError(
                f"bridge endpoint {endpoint.id} ({where}) is absent from "
                f"{OPENAPI_PATH} and not listed in PENDING_BACKEND — contract drift: "
                "the document must declare it or the catalog must record which "
                "backend work package has yet to land it"
            )
        return None
    if not operation.get("responses"):
        raise AssertionError(f"{where}: operation declares no responses in {OPENAPI_PATH}")
    return operation


def _declared(document: dict[str, Any]) -> list[tuple[Endpoint, dict[str, Any]]]:
    pairs: list[tuple[Endpoint, dict[str, Any]]] = []
    for endpoint in BRIDGE_ENDPOINTS:
        operation = _assert_resolved(document, endpoint)
        if operation is not None:
            pairs.append((endpoint, operation))
    return pairs


def _client(send: Any) -> ApiClient:
    settings = load_settings(env={"ORCHESTRATOR_AGENT_TOKEN": TOKEN}, config_path=ABSENT_CONFIG)
    return ApiClient(settings, send=send, sleep=lambda _: None)


# --- representative fixtures --------------------------------------------------

#: Response samples for every declared GET endpoint (validated against the
#: schema its own operation references — adding a declared endpoint without a
#: sample fails loudly and names the endpoint).
RESPONSE_SAMPLES: dict[str, Any] = {
    "health_live": {"status": "ok"},
    "manifest_read": {
        "$schema": "https://orchestrator.local/schemas/manifest.v1.json",
        "schema_version": 1,
        "project_id": "PID00007",
        "project_name": "Tea Factory ERP",
        "orchestrator_api": "http://localhost:8000/api/v1",
        "default_branch": "main",
        "auto_branch_prefix": "feat/PID00007-",
        "audit_required_default": True,
    },
    "project_context": {
        "id": "PID00007",
        "name": "Tea Factory ERP",
        "repo_path": "e:/work/tea-erp",
        "active_status": "active",
        "default_branch": "main",
        "system_prompt_rules": "Stay in scope.",
        "agent_policy": 1,
        "task_counter": 4,
        "created_at": "2026-10-01T09:00:00Z",
        "updated_at": "2026-10-11T18:30:00Z",
    },
    "task_details": {
        "id": "PID00007-T004",
        "project_id": "PID00007",
        "title": "Add invoice export",
        "description": "Export invoices as CSV.",
        "acceptance_criteria": ["CSV downloads with all columns"],
        "target_scope": ["src/billing/**"],
        "test_command": "pytest -q",
        "priority": "medium",
        "state": "pending",
        "version": 3,
        "worker_agent_id": None,
        "worker_session_id": None,
        "claimed_role": None,
        "lease_acquired_at": None,
        "lease_expires_at": None,
        "last_checkpoint_at": None,
        "failure_retry_count": 0,
        "attempt_number": 1,
        "audit_required": True,
        "review_reason": None,
        "latest_feedback": "",
        "merge_status": "none",
        "archived_at": None,
        "created_by": None,
        "created_at": "2026-10-01T09:05:00Z",
        "updated_at": "2026-10-11T18:31:00Z",
        "depends_on": [],
    },
}

#: ``GET /projects/{pid}/work`` shares the tasks envelope (pagination.md:
#: exactly ``results`` + ``next_cursor``), so its items are the same ``Task``
#: payload the ``task_details`` sample already validates.
RESPONSE_SAMPLES["work_list"] = {
    "results": [RESPONSE_SAMPLES["task_details"]],
    "next_cursor": None,
}

#: Request-body samples for declared mutating endpoints whose operation
#: declares a requestBody (validated against the referenced component).
REQUEST_SAMPLES: dict[str, Any] = {
    "task_create_draft": {"title": "Contract-test draft task"},
    "session_open": {"id": "sess-bridge-0001", "transport": "stdio"},
    "claim": {
        "session_id": "sess-bridge-0001",
        "worker_agent_id": "worker-1",
    },
    "release": {"session_id": "sess-bridge-0001", "lease_generation": 1},
}

#: Non-2xx samples (AC 2): three catalog codes against the wire envelope.
ERROR_SAMPLES: dict[str, tuple[int, dict[str, Any]]] = {
    "AUTH_REQUIRED": (
        401,
        {
            "error": {
                "code": "AUTH_REQUIRED",
                "message": "Authentication credentials were not provided.",
                "retryable": False,
                "details": None,
                "correlation_id": "c0a8-4f2e-91d7",
            }
        },
    ),
    "TASK_ALREADY_CLAIMED": (
        409,
        {
            "error": {
                "code": "TASK_ALREADY_CLAIMED",
                "message": "Task PID00007-T004 is held by another worker.",
                "retryable": False,
                "details": {"task_id": "PID00007-T004", "state": "in_progress"},
                "correlation_id": "feed-5eed-0001",
            }
        },
    ),
    "SERVER_ERROR": (
        500,
        {
            "error": {
                "code": "SERVER_ERROR",
                "message": "Internal server error.",
                "retryable": True,
                "details": None,
                "correlation_id": "dead-beef-0001",
            }
        },
    ),
}


# --- document presence and endpoint resolution (AC 1) ------------------------


def test_openapi_document_parses_as_openapi3() -> None:
    document = load_openapi(OPENAPI_PATH)
    assert str(document.get("openapi", "")).startswith("3."), "not an OpenAPI 3.x document"
    assert document["paths"], "document declares no paths"


def test_missing_document_fails_loudly_instead_of_skipping(tmp_path: Path) -> None:
    """Risk note: schema-missing must be an explicit failure, never a skip."""
    with pytest.raises(AssertionError, match="missing"):
        load_openapi(tmp_path / "absent.yaml")


def test_every_bridge_endpoint_is_declared_or_pending(openapi: dict[str, Any]) -> None:
    # _declared() raises for any non-pending absence — that IS the drift check.
    declared = _declared(openapi)
    assert declared, "no bridge endpoint resolves — document or catalog is broken"


def test_undeclared_non_pending_endpoint_fails_with_endpoint_named(
    openapi: dict[str, Any],
) -> None:
    """The failing path names the endpoint (AC 4): fabricated, not in the doc."""
    fabricated = Endpoint("made_up", "GET", "/api/v1/definitely-not-declared")
    with pytest.raises(AssertionError) as excinfo:
        _assert_resolved(openapi, fabricated)
    message = str(excinfo.value)
    assert "made_up" in message and "/api/v1/definitely-not-declared" in message


# --- declared operations: security and idempotency headers (AC 1) ------------


def test_operations_accept_the_bridges_bearer_token(openapi: dict[str, Any]) -> None:
    for endpoint, operation in _declared(openapi):
        security = operation.get("security", [])
        schemes = [set(entry.keys()) for entry in security if isinstance(entry, dict)]
        accepts_bearer = any("bearerAuth" in entry for entry in schemes)
        explicitly_open = any(not entry for entry in schemes)  # `- {}` = open
        if not (accepts_bearer or explicitly_open):
            raise AssertionError(
                f"{endpoint.method} {endpoint.path}: security {security} neither accepts "
                "bearerAuth nor declares itself open — the bridge's Authorization header "
                "would be rejected"
            )


def test_mutating_declared_operations_declare_idempotency_header(
    openapi: dict[str, Any],
) -> None:
    """headers.md: every mutating endpoint accepts Idempotency-Key; a schema
    that forgets to declare it would silently disable retry safety."""
    for endpoint, operation in _declared(openapi):
        if not endpoint.mutating:
            continue
        parameters = operation.get("parameters", [])
        declared_names = {
            (entry.get("name"), entry.get("in")) for entry in parameters if isinstance(entry, dict)
        }
        if ("Idempotency-Key", "header") not in declared_names:
            raise AssertionError(
                f"{endpoint.method} {endpoint.path}: the OpenAPI operation does not "
                "declare the Idempotency-Key header parameter (headers.md requires "
                "every mutating endpoint to accept it) — field 'parameters'"
            )


# --- client behavior: the headers actually sent (AC 1) -----------------------


def test_client_requests_match_declared_operations(openapi: dict[str, Any]) -> None:
    for endpoint, _ in _declared(openapi):
        request = _single_request(endpoint)
        assert request["method"] == endpoint.method
        # Path matches the OpenAPI template exactly (origin join, transport docstring).
        assert urlsplit(str(request["url"])).path == endpoint.path
        headers = request["headers"]
        assert headers["Authorization"] == f"Bearer {TOKEN}"
        assert headers[API_VERSION_HEADER] == EXPECTED_API_VERSION
        assert headers[CORRELATION_HEADER]
        assert ("Idempotency-Key" in headers) is endpoint.mutating, (
            f"{endpoint.method} {endpoint.path}: idempotency header presence must "
            "match headers.md's mutating-verb rule"
        )


def _single_request(endpoint: Endpoint) -> dict[str, Any]:
    """Drive one request through the real client; return what hit the boundary."""
    sent: list[dict[str, Any]] = []

    def send(
        method: str, url: str, headers: Any, body: bytes | None, timeout: float
    ) -> WireResponse:
        sent.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        return WireResponse(200, {}, b"{}")

    _client(send).request(endpoint.method, endpoint.path)
    assert len(sent) == 1, f"{endpoint.id}: expected exactly one attempt"
    return sent[0]


# --- request and response shapes (AC 1) --------------------------------------


def test_request_body_samples_match_schema(openapi: dict[str, Any]) -> None:
    checked = 0
    for endpoint, operation in _declared(openapi):
        if not endpoint.mutating:
            continue
        request_body = operation.get("requestBody")
        if not isinstance(request_body, dict):
            continue  # a body-less mutation declares none — nothing to validate
        schema = request_body.get("content", {}).get("application/json", {}).get("schema", {})
        component = str(schema.get("$ref", "")).rsplit("/", 1)[-1]
        sample = REQUEST_SAMPLES.get(endpoint.id)
        assert component and sample is not None, (
            f"{endpoint.method} {endpoint.path}: declares a JSON requestBody but no "
            f"REQUEST_SAMPLES entry named '{endpoint.id}' exists — add the sample "
            "(the contract test needs it to keep this endpoint honest)"
        )
        assert_contract(
            sample,
            component,
            where=f"request body of {endpoint.method} {endpoint.path}",
            document=openapi,
        )
        checked += 1
    assert checked, "no declared mutating endpoint with a body — suite lost its subject"


def test_response_samples_match_schema(openapi: dict[str, Any]) -> None:
    checked = 0
    for endpoint, operation in _declared(openapi):
        if endpoint.mutating:
            continue
        schema = (
            operation.get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        component = str(schema.get("$ref", "")).rsplit("/", 1)[-1]
        sample = RESPONSE_SAMPLES.get(endpoint.id)
        assert component and sample is not None, (
            f"{endpoint.method} {endpoint.path}: declared GET without a "
            f"RESPONSE_SAMPLES entry named '{endpoint.id}' — add the sample so the "
            "response schema stays checked"
        )
        assert_contract(
            sample,
            component,
            where=f"200 response of {endpoint.method} {endpoint.path}",
            document=openapi,
        )
        checked += 1
    assert checked, "no declared GET endpoint — suite lost its subject"


# --- error envelope: samples, catalog sync, client round-trip (AC 2) ---------


def test_error_envelope_samples_validate(openapi: dict[str, Any]) -> None:
    for code, (status, sample) in ERROR_SAMPLES.items():
        assert sample["error"]["code"] == code
        assert_contract(
            sample,
            "ErrorEnvelope",
            where=f"{status} error envelope ({code})",
            document=openapi,
        )


def test_error_samples_round_trip_through_the_client_parser(
    openapi: dict[str, Any],
) -> None:
    """The exact documents the schema approves are parsed by the client into
    the same canonical code — schema, backend and bridge agree end to end."""
    for code, (status, sample) in ERROR_SAMPLES.items():
        error = _parsed_error(status, sample)
        assert error.code is ErrorCode(code)
        assert error.correlation_id == sample["error"]["correlation_id"]
        assert error.retryable is sample["error"]["retryable"]


def _parsed_error(status: int, sample: dict[str, Any]) -> ApiError:
    """Feed one envelope sample through the real client parser."""
    body = json.dumps(sample).encode("utf-8")

    def send(
        method: str, url: str, headers: Any, payload: bytes | None, timeout: float
    ) -> WireResponse:
        return WireResponse(status, {}, body)

    with pytest.raises(ApiError) as excinfo:
        _client(send).request("GET", "/api/v1/tasks/PID00007-T004")
    return excinfo.value


def test_bridge_catalog_matches_schema_code_enum(openapi: dict[str, Any]) -> None:
    """NFR-11 drift check: the closed catalogs on both sides stay identical."""
    enum = openapi["components"]["schemas"]["CodeEnum"]["enum"]
    bridge = [code.value for code in CANONICAL_ERROR_CODES]
    missing_from_bridge = sorted(set(enum) - set(bridge))
    missing_from_schema = sorted(set(bridge) - set(enum))
    assert not missing_from_bridge, (
        f"schema CodeEnum codes missing from the bridge catalog: {missing_from_bridge}"
    )
    assert not missing_from_schema, (
        f"bridge catalog codes missing from schema CodeEnum: {missing_from_schema}"
    )
    assert len(bridge) == 19, "error-envelope.md publishes exactly 19 codes"


# --- the deliberate-mismatch path (AC 4) -------------------------------------


def test_deliberate_mismatch_fails_naming_endpoint_and_field(
    openapi: dict[str, Any],
) -> None:
    broken = deepcopy(ERROR_SAMPLES["AUTH_REQUIRED"][1])
    del broken["error"]["correlation_id"]  # violate the schema's required list
    with pytest.raises(AssertionError) as excinfo:
        assert_contract(
            broken,
            "ErrorEnvelope",
            where="401 error envelope (AUTH_REQUIRED)",
            document=openapi,
        )
    message = str(excinfo.value)
    assert "AUTH_REQUIRED" in message  # endpoint/instance named
    assert "correlation_id" in message  # field named
