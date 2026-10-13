"""MT-3.1-03 — policy validation: glob discipline + stated bounds (WP-3.1).

The MT's test battery (``pytest backend/tests -k policy_validation``):

* the three glob fields reject malformed syntax, absolute paths and
  ``..`` traversal (Section 12.3) with ``VALIDATION_ERROR`` and
  per-index ``details`` — the same rules the target-scope validator in
  ``apps.tasks`` states, now shared through
  ``apps.projects.services.globs`` (the single-matcher module WP-3.4
  must reuse);
* ``auditor_min_confidence`` stays 1–5; the positive-integer fields stay
  >= 1 (``max_concurrent_tasks`` >= 0 per G-26); enums stay the closed
  Section 7.2 vocabularies;
* ``lease_max_total_minutes >= lease_duration_minutes`` holds across a
  patch — the merged row can never be put into an invalid combination
  by patching one side alone;
* the stock defaults and every preset payload pass the endpoint's own
  validation unmodified (backward-compat rule + MT-3.1-02 AC);
* the matcher itself works (``glob_matches``) — WP-3.4's Policy Engine
  imports it instead of writing a second matcher.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.projects.policy_presets import list_presets, preset_glob_fields
from apps.projects.serializers.policy import ProjectPolicySerializer
from apps.projects.services.globs import glob_matches, validate_glob_list
from tests.test_project_api import _create, _envelope
from tests.test_project_models import POLICY_DEFAULTS

PASSWORD = "policy-validation-tests-1!"  # pragma: allowlist secret


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport)."""
    from apps.accounts.models import User

    User.objects.create_user("policy-validation-owner", None, PASSWORD)
    api = APIClient()
    response = api.post(
        "/api/v1/auth/login",
        {"username": "policy-validation-owner", "password": PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    return api


def _policy_url(owner_client: APIClient) -> str:
    project = _create(owner_client)
    return f"/api/v1/projects/{project['id']}/policy"


def _patch(owner_client: APIClient, url: str, body: dict[str, Any]) -> Any:
    return owner_client.patch(url, body, format="json")


# --- the shared matcher (WP-3.4's import target) ----------------------------


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("**/*.py", "src/deep/mod.py", True),
        ("**/*.py", "mod.py", True),
        ("src/*.py", "src/a/b.py", False),  # single star never crosses '/'
        ("src/*.py", "src/a.py", True),
        ("src/**", "src/a/b/c.py", True),
        ("**/migrations/*.py", "app/migrations/0001_initial.py", True),
        ("**/migrations/*.py", "app/models.py", False),
        ("feat/*", "feat/PID00001-add-auth", True),
        ("docs/?.md", "docs/a.md", True),
        ("docs/?.md", "docs/ab.md", False),
        ("**/*[0-9].log", "logs/app1.log", True),
        ("**/*[0-9].log", "logs/appX.log", False),
        (".env*", ".env", True),
        (".env*", ".env.production", True),
        (".env*", "config/.env", False),  # anchored: no implicit '**/'
    ],
)
def test_glob_matches_follows_section_12_3_semantics(
    pattern: str, path: str, expected: bool
) -> None:
    """The single matcher anchors full paths; '*' is one segment, '**' many."""
    assert glob_matches(pattern, path) is expected


# --- validate_glob_list unit level ------------------------------------------


def test_validate_glob_list_returns_cleaned_copies() -> None:
    cleaned = validate_glob_list([" infra/* ", ".env*"], field="critical_path_globs")
    assert cleaned == ["infra/*", ".env*"]  # whitespace-trimmed, order kept


@pytest.mark.parametrize(
    "bad_glob",
    [
        "/etc/**",  # absolute (POSIX)
        "C:/win/**",  # absolute (drive letter)
        "../secrets/**",  # traversal
        "app/../../x",  # traversal mid-path
        "app\\**",  # backslash separator
        "**bad/**/x",  # '**' not a whole segment
        "docs/[abc",  # unterminated character class
        "",  # empty
    ],
)
def test_validate_glob_list_rejects_section_12_3_violations(bad_glob: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_glob_list([bad_glob], field="critical_path_globs")
    payload = cast(dict[str, Any], excinfo.value.detail)
    detail = payload["critical_path_globs"]
    assert isinstance(detail, dict) and "0" in detail


def test_validate_glob_list_reports_the_offending_index() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_glob_list(["infra/*", "../escape", ".env*"], field="critical_path_globs")
    payload = cast(dict[str, Any], excinfo.value.detail)
    detail = cast(dict[str, Any], payload["critical_path_globs"])
    assert set(detail) == {"1"}, "only the offending entry is flagged"


def test_validate_glob_list_caps_entry_count_and_length() -> None:
    with pytest.raises(ValidationError):
        validate_glob_list(["a/*"] * 65, field="migration_path_globs")
    with pytest.raises(ValidationError):
        validate_glob_list(["x" * 501], field="migration_path_globs")


# --- PATCH API: glob syntax discipline --------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"critical_path_globs": ["**bad/**/x"]},  # malformed '**'
        {"critical_path_globs": ["/etc/**"]},  # absolute
        {"migration_path_globs": ["../migrations/*"]},  # traversal
        {"sensitive_config_globs": ["app\\secrets\\*"]},  # backslash
        {"critical_path_globs": ["docs/[abc"]},  # unterminated class
    ],
)
def test_patch_rejects_invalid_globs_with_catalog_code(
    owner_client: APIClient, body: dict[str, list[str]]
) -> None:
    url = _policy_url(owner_client)
    response = _patch(owner_client, url, body)
    assert response.status_code == status.HTTP_400_BAD_REQUEST, body
    assert _envelope(response)["code"] == "VALIDATION_ERROR", body
    field = next(iter(body))
    assert field in response.json()["error"]["details"], field


def test_invalid_glob_reports_the_offending_index(owner_client: APIClient) -> None:
    """details = {field: {index: [problems]}} — the target-scope shape."""
    url = _policy_url(owner_client)
    response = _patch(owner_client, url, {"critical_path_globs": ["infra/*", "/etc/**", ".env*"]})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    details = cast(dict[str, Any], response.json()["error"]["details"])
    assert set(details["critical_path_globs"]) == {"1"}, response.json()


def test_patch_accepts_section_12_3_clean_globs(owner_client: APIClient) -> None:
    url = _policy_url(owner_client)
    clean = ["**/*.py", "src/?eb/**", "docs/[ab]x*", ".env*"]
    for field in ("critical_path_globs", "migration_path_globs", "sensitive_config_globs"):
        response = _patch(owner_client, url, {field: clean})
        assert response.status_code == status.HTTP_200_OK, response.content
        assert response.json()[field] == clean


# --- PATCH API: bounds, enums, cross-field ----------------------------------


def test_patch_enforces_the_stated_numeric_bounds(owner_client: APIClient) -> None:
    """1-5 confidence; positive durations/retries/thresholds; concurrency >= 0."""
    url = _policy_url(owner_client)
    for body in (
        {"auditor_min_confidence": 0},
        {"auditor_min_confidence": 6},
        {"lease_duration_minutes": 0},
        {"max_retries": 0},
        {"autonomous_diff_threshold_lines": 0},
        {"stalled_after_minutes": 0},
    ):
        response = _patch(owner_client, url, body)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, body
        assert _envelope(response)["code"] == "VALIDATION_ERROR", body

    assert _patch(owner_client, url, {"auditor_min_confidence": 5}).status_code == 200
    assert _patch(owner_client, url, {"max_concurrent_tasks": 0}).status_code == 200


def test_patch_enforces_the_closed_enum_vocabularies(owner_client: APIClient) -> None:
    url = _policy_url(owner_client)
    for body in (
        {"lease_extension_mode": "sometimes"},
        {"merge_strategy": "rebase"},
    ):
        response = _patch(owner_client, url, body)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, body
        assert _envelope(response)["code"] == "VALIDATION_ERROR", body


def test_lease_cap_must_cover_the_base_duration(owner_client: APIClient) -> None:
    """Cross-field: total >= duration on the merged row, per MT-3.1-03."""
    url = _policy_url(owner_client)

    too_small_cap = _patch(owner_client, url, {"lease_max_total_minutes": 10})
    assert too_small_cap.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(too_small_cap)["code"] == "VALIDATION_ERROR"
    assert "lease_max_total_minutes" in too_small_cap.json()["error"]["details"]

    too_long_duration = _patch(owner_client, url, {"lease_duration_minutes": 300})
    assert too_long_duration.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(too_long_duration)["code"] == "VALIDATION_ERROR"

    # A patch that keeps the invariant passes.
    ok = _patch(owner_client, url, {"lease_duration_minutes": 60})
    assert ok.status_code == status.HTTP_200_OK, ok.content
    both = _patch(owner_client, url, {"lease_duration_minutes": 90, "lease_max_total_minutes": 120})
    assert both.status_code == status.HTTP_200_OK, both.content


# --- defaults and presets pass validation unmodified ------------------------


def test_stock_defaults_pass_the_endpoint_serializer() -> None:
    """The WP-1.3 default payload validates through the WP-3.1 serializer."""
    serializer = ProjectPolicySerializer(data=dict(POLICY_DEFAULTS))
    serializer.is_valid(raise_exception=True)


@pytest.mark.parametrize("preset", list_presets(), ids=lambda p: p.id)
def test_every_preset_payload_passes_the_endpoint_serializer(
    preset: Any,
) -> None:
    """MT-3.1-02 AC via MT-3.1-03's rules: preset triple + defaults = valid."""
    body: dict[str, Any] = dict(POLICY_DEFAULTS)
    body.update(preset_glob_fields(preset))
    serializer = ProjectPolicySerializer(data=body)
    serializer.is_valid(raise_exception=True)
