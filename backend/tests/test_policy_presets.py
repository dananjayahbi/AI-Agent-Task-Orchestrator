"""MT-3.1-02 — framework policy presets, selectable at project creation (WP-3.1).

The MT's test battery (``pytest backend/tests -k policy_presets``):

* the library ships at least Django / Next.js / Flutter, each covering
  all three Section 7.2 glob categories (critical / migration /
  sensitive), versioned;
* every preset glob passes the Section 12.3 validator the PATCH endpoint
  uses — presets cannot smuggle an invalid glob past MT-3.1-03 (the
  acceptance the MT calls out explicitly; the same check also runs at
  write time via ``preset_glob_fields``, so a drifted preset is refused
  at runtime, not only in tests);
* a preset selected at project creation writes exactly the three glob
  fields and leaves every other policy field at its Section 7.2 default;
  omitting it reproduces the stock defaults (backward compat);
* unknown preset ids answer the catalog ``VALIDATION_ERROR``;
* ``PATCH /projects/{pid}/policy`` applies a preset in one action, and
  combining it with explicit glob fields is refused rather than silently
  ordered (the conflict rule);
* the DTO listing surface renders the whole library for clients.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.events.models import Event
from apps.projects.policy_presets import (
    DJANGO,
    PRESET_IDS,
    PRESET_LIBRARY_VERSION,
    PRESETS,
    PolicyPreset,
    get_preset,
    list_presets,
    preset_glob_fields,
)
from apps.projects.serializers.policy import ProjectPolicySerializer, render_presets
from apps.projects.services.globs import validate_glob_list
from tests.test_project_api import _envelope
from tests.test_project_models import POLICY_DEFAULTS

PASSWORD = "policy-preset-tests-1!"  # pragma: allowlist secret

GLOB_FIELDS = ("critical_path_globs", "migration_path_globs", "sensitive_config_globs")


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport)."""
    from apps.accounts.models import User

    User.objects.create_user("preset-owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "preset-owner", "password": PASSWORD})
    assert response.status_code == status.HTTP_200_OK, response.content
    return api


def _post_create(owner_client: APIClient, **extra: Any) -> Any:
    payload = {
        "name": "Preset project",
        "repo_path": "/srv/repos/preset-project",
        "default_branch": "main",
        **extra,
    }
    return owner_client.post("/api/v1/projects", payload, format="json")


def _get_policy(owner_client: APIClient, project_id: str) -> dict[str, Any]:
    response = owner_client.get(f"/api/v1/projects/{project_id}/policy")
    assert response.status_code == status.HTTP_200_OK, response.content
    return cast(dict[str, Any], response.json())


# --- the library as data (AC: three frameworks, all three categories) -------


def test_library_ships_the_three_required_frameworks_versioned() -> None:
    """MT AC: Django, Next.js, Flutter exist as versioned data entries."""
    assert set(PRESET_IDS) == {"django", "nextjs", "flutter"}
    assert PRESET_LIBRARY_VERSION >= 1
    assert set(PRESETS) == set(PRESET_IDS)
    assert isinstance(PRESETS["django"], PolicyPreset)


def test_every_preset_covers_all_three_glob_categories() -> None:
    """Each preset supplies non-empty critical / migration / sensitive lists."""
    for preset in list_presets():
        for field in GLOB_FIELDS:
            globs = getattr(preset, field)
            assert globs, f"{preset.id}.{field} must not be empty"


def test_every_preset_glob_passes_the_section_12_3_validator() -> None:
    """MT acceptance: no preset glob violates MT-3.1-03's rules."""
    for preset in list_presets():
        for field in GLOB_FIELDS:
            validate_glob_list(getattr(preset, field), field=field)


def test_preset_glob_copies_are_fresh_per_call() -> None:
    """No shared mutable lists: callers can never corrupt the library."""
    first = preset_glob_fields(DJANGO)
    second = preset_glob_fields(DJANGO)
    assert first == second
    first["critical_path_globs"].append("mutated/*")
    assert "mutated/*" not in preset_glob_fields(DJANGO)["critical_path_globs"]


# --- creation-time selection (AC: preset writes the three glob fields) ------


def test_create_with_policy_preset_writes_the_three_glob_fields(owner_client: APIClient) -> None:
    """MT AC: the new policy carries the preset globs, others stay default."""
    response = _post_create(owner_client, policy_preset="django")
    assert response.status_code == status.HTTP_201_CREATED, response.content
    project_id = cast(str, response.json()["id"])

    body = _get_policy(owner_client, project_id)
    preset = get_preset("django")
    assert body["critical_path_globs"] == list(preset.critical_path_globs)
    assert body["migration_path_globs"] == list(preset.migration_path_globs)
    assert body["sensitive_config_globs"] == list(preset.sensitive_config_globs)

    # Blast-radius rule: every non-glob field keeps its Section 7.2 default.
    for field in POLICY_DEFAULTS:
        if field not in GLOB_FIELDS:
            assert body[field] == POLICY_DEFAULTS[field], field


def test_each_framework_preset_applies_at_creation(owner_client: APIClient) -> None:
    """django / nextjs / flutter each land their own triple."""
    for preset_id in ("django", "nextjs", "flutter"):
        response = _post_create(
            owner_client,
            name=f"Preset {preset_id}",
            repo_path=f"/srv/repos/preset-{preset_id}",
            policy_preset=preset_id,
        )
        assert response.status_code == status.HTTP_201_CREATED, response.content
        body = _get_policy(owner_client, cast(str, response.json()["id"]))
        preset = get_preset(preset_id)
        for field in GLOB_FIELDS:
            assert body[field] == list(getattr(preset, field)), f"{preset_id}.{field}"


def test_create_without_preset_keeps_the_stock_defaults(owner_client: APIClient) -> None:
    """Backward compat: no selection = the exact WP-1.3 policy."""
    response = _post_create(owner_client)
    assert response.status_code == status.HTTP_201_CREATED, response.content

    body = _get_policy(owner_client, cast(str, response.json()["id"]))
    for field in GLOB_FIELDS:
        assert body[field] == POLICY_DEFAULTS[field], field


def test_create_with_unknown_preset_is_a_catalog_validation_error(
    owner_client: APIClient,
) -> None:
    """Unknown id: VALIDATION_ERROR with the offending field in details."""
    response = _post_create(owner_client, policy_preset="rails")
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.content
    assert _envelope(response)["code"] == "VALIDATION_ERROR"
    assert "policy_preset" in response.json()["error"]["details"]


def test_preset_selection_does_not_leak_into_the_policy_get(owner_client: APIClient) -> None:
    """policy_preset is write-only: GET stays exactly the Section 7.2 set."""
    created = _post_create(owner_client, policy_preset="flutter")
    assert created.status_code == status.HTTP_201_CREATED, created.content

    body = _get_policy(owner_client, cast(str, created.json()["id"]))
    assert set(body) == set(POLICY_DEFAULTS)
    assert "policy_preset" not in body


def test_create_event_records_the_selected_preset(owner_client: APIClient) -> None:
    """Audit trail (12.5): project.created notes how the globs got set."""
    created = _post_create(owner_client, policy_preset="nextjs")
    assert created.status_code == status.HTTP_201_CREATED, created.content

    event = Event.objects.filter(project_id=created.json()["id"], type="project.created").get()
    assert event.data == {"policy_preset": "nextjs"}


def test_create_event_has_no_preset_key_when_omitted(owner_client: APIClient) -> None:
    """No selection = no data payload, exactly the WP-1.3 event shape."""
    created = _post_create(owner_client)
    assert created.status_code == status.HTTP_201_CREATED, created.content

    event = Event.objects.filter(project_id=created.json()["id"], type="project.created").get()
    assert event.data == {}


# --- update-time selection (apply a preset in one PATCH action) -------------


def test_patch_policy_applies_a_preset_in_one_action(owner_client: APIClient) -> None:
    """One PATCH with policy_preset fills the three glob fields; rest stable."""
    created = _post_create(owner_client)
    assert created.status_code == status.HTTP_201_CREATED, created.content
    project_id = cast(str, created.json()["id"])
    before = _get_policy(owner_client, project_id)

    patched = owner_client.patch(
        f"/api/v1/projects/{project_id}/policy",
        {"policy_preset": "flutter"},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK, patched.content

    after = _get_policy(owner_client, project_id)
    preset = get_preset("flutter")
    for field in GLOB_FIELDS:
        assert after[field] == list(getattr(preset, field)), field
    changed = {key for key in before if before[key] != after[key]}
    assert changed == set(GLOB_FIELDS), "the preset touches nothing else"


def test_patch_rejects_preset_combined_with_explicit_globs(owner_client: APIClient) -> None:
    """Conflict rule: no implicit ordering between preset and explicit lists."""
    created = _post_create(owner_client)
    assert created.status_code == status.HTTP_201_CREATED, created.content
    url = f"/api/v1/projects/{created.json()['id']}/policy"
    before = _get_policy(owner_client, cast(str, created.json()["id"]))

    response = owner_client.patch(
        url,
        {"policy_preset": "django", "critical_path_globs": ["infra/*"]},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.content
    assert _envelope(response)["code"] == "VALIDATION_ERROR"
    assert "policy_preset" in response.json()["error"]["details"]
    assert _get_policy(owner_client, cast(str, created.json()["id"])) == before


def test_patch_with_unknown_preset_is_rejected(owner_client: APIClient) -> None:
    """The PATCH surface shares the catalog answer for unknown ids."""
    created = _post_create(owner_client)
    assert created.status_code == status.HTTP_201_CREATED, created.content

    response = owner_client.patch(
        f"/api/v1/projects/{created.json()['id']}/policy",
        {"policy_preset": "sveltekit"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.content
    assert _envelope(response)["code"] == "VALIDATION_ERROR"


def test_preset_patch_event_lists_the_three_glob_fields(owner_client: APIClient) -> None:
    """The audit trail names the fields the preset actually changed."""
    created = _post_create(owner_client)
    assert created.status_code == status.HTTP_201_CREATED, created.content
    project_id = cast(str, created.json()["id"])

    owner_client.patch(
        f"/api/v1/projects/{project_id}/policy",
        {"policy_preset": "django"},
        format="json",
    )
    event = Event.objects.filter(project_id=project_id, type="project.updated").last()
    assert event is not None
    assert event.data == {"scope": "policy", "fields": sorted(GLOB_FIELDS)}


# --- the DTO listing surface + unit-level guards ----------------------------


def test_render_presets_dto_covers_the_library() -> None:
    """The listing DTO renders id/title/description and every glob list."""
    rows = render_presets()
    assert [row["id"] for row in rows] == list(PRESET_IDS)
    by_id = {row["id"]: row for row in rows}
    for preset_id, preset in PRESETS.items():
        row = by_id[preset_id]
        assert row["title"] == preset.title
        assert row["description"] == preset.description
        for field in GLOB_FIELDS:
            assert row[field] == list(getattr(preset, field)), field


def test_every_preset_payload_is_valid_through_the_policy_serializer() -> None:
    """Preset triple + stock defaults = a serializer-valid policy body."""
    for preset in list_presets():
        body: dict[str, Any] = dict(POLICY_DEFAULTS)
        body.update(preset_glob_fields(preset))
        ProjectPolicySerializer(data=body).is_valid(raise_exception=True)


def test_get_preset_rejects_unknown_ids_with_the_catalog_shape() -> None:
    """Direct service callers get the same answer as the API boundary."""
    from rest_framework.exceptions import ValidationError

    with pytest.raises(ValidationError) as excinfo:
        get_preset("rails")
    assert "policy_preset" in excinfo.value.detail
