"""SPECTACULAR postprocessing hooks (NFR-11 — one document, two clients).

``simplify_nullable_enums`` flattens drf-spectacular's nullable-enum shape

    {nullable: true, oneOf: [{$ref: XEnum}, {$ref: NullEnum}]}

into the conventional OpenAPI 3.0 nullable-$ref shape

    {nullable: true, allOf: [{$ref: XEnum}]}

Wire semantics are identical (value is XEnum or null), but the ``oneOf``
composition is mishandled by pinned client generators: openapi-generator
7.26.0's Dart output references ``PolicyDecisionEnum`` without importing
its model file, so the mobile client fails to compile
(``dart run tool/openapi_client.dart check``). The ``allOf`` shape is
generated correctly by both consumers (hey-api and openapi-generator) and
is what every pre-batch-6 nullable field already looked like. The
``NullEnum`` component is dropped when no reference to it remains.
"""

from __future__ import annotations

from typing import Any

_NULL_ENUM_REF = "#/components/schemas/NullEnum"


def _contains_null_enum_ref(node: Any) -> bool:
    if isinstance(node, dict):
        if node.get("$ref") == _NULL_ENUM_REF:
            return True
        return any(_contains_null_enum_ref(value) for value in node.values())
    if isinstance(node, list):
        return any(_contains_null_enum_ref(value) for value in node)
    return False


def _flatten(node: Any) -> None:
    """Recursively rewrite oneOf+NullEnum nullable enums to nullable+allOf."""
    if isinstance(node, dict):
        one_of = node.get("oneOf")
        if isinstance(one_of, list) and _contains_null_enum_ref(one_of):
            others = [
                entry
                for entry in one_of
                if not (isinstance(entry, dict) and entry.get("$ref") == _NULL_ENUM_REF)
            ]
            if len(others) == 1:
                node.pop("oneOf")
                node["nullable"] = True
                node["allOf"] = others
                return
        for value in node.values():
            _flatten(value)
    elif isinstance(node, list):
        for value in node:
            _flatten(value)


def simplify_nullable_enums(
    result: dict[str, Any],
    generator: Any,
    request: Any,
    public: bool,
) -> dict[str, Any]:
    """Postprocessing hook registered in SPECTACULAR_SETTINGS."""
    _flatten(result)
    if not _contains_null_enum_ref(result):
        result.get("components", {}).get("schemas", {}).pop("NullEnum", None)
    return result
