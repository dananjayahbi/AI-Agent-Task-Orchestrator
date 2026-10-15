"""MT-5.4-05 — per-event-type notification preferences (storage, endpoint, dispatch consultation).

Section 9.8's preference set as one account-level record (Section 13.1 web
settings and Section 14.1 mobile toggles edit the same rows), OQ-13's
decided defaults honored (escalations on, completion digest off), and the
dispatch-path consultation placed exactly where the MT's Scope fixes it —
after trigger selection, **before dedupe/send**, so a disabled type records
zero FCM attempts and zero rows in either operational table (the Section 17
metric cannot be skewed; nothing is queued, so re-enabling notifies only
events dispatched afterwards).

Authorization follows the recorded ruling in
``HasNotificationPreferencesAccess``: Owner and Device (the two named
surfaces), agents denied, anonymous → AUTH_REQUIRED.

Run with ``pytest backend/tests -k notification_preferences -q``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken, Device, TokenKind, User
from apps.accounts.services.tokens import hash_token
from apps.notifications import dispatch as dispatch_module
from apps.notifications.models import (
    NotificationPreference,
    PushDedupeRecord,
    PushDeliveryRecord,
)
from apps.notifications.preferences import (
    DEFAULT_ENABLED,
    NOTIFICATION_EVENT_TYPES,
    get_or_create_preference,
    preference_enabled,
    resolve_preference_key,
)
from apps.notifications.sender import set_fcm_transport
from apps.projects.models import Project
from apps.tasks.models import Task, TaskState
from tests.test_fcm_sender import FakeTransport
from tests.wp15_helpers import make_project, make_task
from tests.wp16_helpers import restore_lease_registry  # noqa: F401  (autouse)
from tests.wp33_helpers import (
    JsonAPIClient,
    agent_client,
    issue_agent_token,
    login_owner_client,
)

pytestmark = pytest.mark.django_db

PREFS_URL = "/api/v1/notifications/preferences"


@pytest.fixture(autouse=True)
def clean_seams() -> Iterator[None]:
    """Keep the process-global push transport seam clean across the suite."""
    try:
        yield
    finally:
        set_fcm_transport(None)


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — keep budgets fresh (suite-wide)."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def project(db: None) -> Project:
    """One project row with the default policy."""
    return make_project(name="WP-5.4 preferences")


@pytest.fixture
def task(project: Project) -> Task:
    """A review-state row the dispatch trigger names (title source)."""
    return make_task(project, 1, state=TaskState.IN_HUMAN_REVIEW, title="Prefs task")


def _register_device(user: User, *, push_token: str) -> Device:
    """One active device row (WP-5.3's shape)."""
    token_row = ApiToken.objects.create(
        kind=TokenKind.DEVICE,
        user=user,
        hash=hash_token(f"credential-{user.pk}-{push_token}"),
        project_id=None,
    )
    return Device.objects.create(
        user=user, platform="android", push_token=push_token, token=token_row
    )


@pytest.fixture
def devices(db: None) -> tuple[Device, Device]:
    """Two live phones on one owner."""
    user = User.objects.create_user(
        "wp5405-owner", None, "pw-wp5405-preferences-1"
    )  # pragma: allowlist secret
    return (
        _register_device(user, push_token="prefs-phone-a"),
        _register_device(user, push_token="prefs-phone-b"),
    )


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport)."""
    return login_owner_client()


def _trigger(
    task: Task,
    *,
    event_type: str = "task.transitioned",
    reason_code: str = "audit_escalated",
    state_version: int | None = None,
) -> dict[str, Any]:
    """A dispatcher-shaped trigger (the Section 9.8 seam payload)."""
    return {
        "event_type": event_type,
        "project_id": task.project_id,
        "task_id": task.pk,
        "state_version": state_version if state_version is not None else task.version,
        "reason_code": reason_code,
    }


def _set(owner_client: JsonAPIClient, event_type: str, enabled: bool) -> None:
    response = owner_client.put(
        PREFS_URL,
        {"preferences": [{"event_type": event_type, "enabled": enabled}]},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.content


# --- defaults (AC 1 / OQ-13) -------------------------------------------------


def test_get_returns_the_full_set_with_oq13_defaults(owner_client: JsonAPIClient) -> None:
    """Escalations on, digest off — the closed Section 9.8 set, in order."""
    response = owner_client.get(PREFS_URL)
    assert response.status_code == status.HTTP_200_OK, response.content
    rows = response.json()["preferences"]
    assert [row["event_type"] for row in rows] == list(NOTIFICATION_EVENT_TYPES)
    assert {row["event_type"]: row["enabled"] for row in rows} == DEFAULT_ENABLED
    # The read materialized the rows so every surface sees real storage.
    assert NotificationPreference.objects.count() == len(NOTIFICATION_EVENT_TYPES)


def test_get_twice_materializes_each_row_once(owner_client: JsonAPIClient) -> None:
    """Idempotent read: defaults are stored once, never re-seeded."""
    owner_client.get(PREFS_URL)
    owner_client.get(PREFS_URL)
    assert NotificationPreference.objects.count() == len(NOTIFICATION_EVENT_TYPES)


def test_defaults_honor_oq13_without_the_endpoint(owner_client: JsonAPIClient) -> None:
    """Stored default posture: every escalation toggle starts enabled."""
    assert preference_enabled({"event_type": "task.transitioned", "reason_code": "audit_escalated"})
    assert preference_enabled({"event_type": "merge.failed", "reason_code": "merge_failed"})
    assert preference_enabled({"event_type": "task.transitioned", "reason_code": "retry_exhausted"})
    row = get_or_create_preference("completion_digest")
    assert row.enabled is False  # OQ-13: digest off by default


# --- endpoint round trip and validation -------------------------------------


def test_put_round_trip_persists_and_answers_with_the_full_set(
    owner_client: JsonAPIClient,
) -> None:
    """Update a subset; the response (and the next read) carry everything."""
    response = owner_client.put(
        PREFS_URL,
        {
            "preferences": [
                {"event_type": "in_human_review", "enabled": False},
                {"event_type": "completion_digest", "enabled": True},
            ]
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    state = {row["event_type"]: row["enabled"] for row in response.json()["preferences"]}
    assert state["in_human_review"] is False
    assert state["completion_digest"] is True
    assert state["merge_failure"] is True  # untouched rows answer too

    reread = {
        row["event_type"]: row["enabled"]
        for row in owner_client.get(PREFS_URL).json()["preferences"]
    }
    assert reread == state


def test_put_rejects_an_unknown_event_type(owner_client: JsonAPIClient) -> None:
    """Only the backend's closed set exists — never an invented type."""
    response = owner_client.put(
        PREFS_URL,
        {"preferences": [{"event_type": "quantum_digest", "enabled": True}]},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_put_rejects_unknown_fields_duplicates_and_empty_lists(
    owner_client: JsonAPIClient,
) -> None:
    """Strict input: unknown keys, repeated types and empty updates refuse."""
    unknown_top = owner_client.put(
        PREFS_URL,
        {"preferences": [{"event_type": "in_human_review", "enabled": True}], "mode": "all"},
        format="json",
    )
    assert unknown_top.status_code == status.HTTP_400_BAD_REQUEST
    assert unknown_top.json()["error"]["code"] == "VALIDATION_ERROR"

    unknown_item = owner_client.put(
        PREFS_URL,
        {"preferences": [{"event_type": "in_human_review", "enabled": True, "forever": True}]},
        format="json",
    )
    assert unknown_item.status_code == status.HTTP_400_BAD_REQUEST

    duplicate = owner_client.put(
        PREFS_URL,
        {
            "preferences": [
                {"event_type": "in_human_review", "enabled": True},
                {"event_type": "in_human_review", "enabled": False},
            ]
        },
        format="json",
    )
    assert duplicate.status_code == status.HTTP_400_BAD_REQUEST
    assert duplicate.json()["error"]["code"] == "VALIDATION_ERROR"

    empty = owner_client.put(PREFS_URL, {"preferences": []}, format="json")
    assert empty.status_code == status.HTTP_400_BAD_REQUEST


# --- authorization (the recorded matrix ruling) ------------------------------


def test_owner_and_device_read_and_adjust_agents_are_denied(
    owner_client: JsonAPIClient, project: Project, db: None
) -> None:
    """Owner session + device bearer pass; agents get ROLE_NOT_PERMITTED."""
    # Owner: both verbs.
    assert owner_client.get(PREFS_URL).status_code == status.HTTP_200_OK
    assert (
        owner_client.put(
            PREFS_URL,
            {"preferences": [{"event_type": "merge_failure", "enabled": False}]},
            format="json",
        ).status_code
        == status.HTTP_200_OK
    )

    # Device (the mobile toggles' channel): registration issues the token.
    registration = owner_client.post(
        "/api/v1/devices", {"platform": "android", "push_token": "prefs-device-1"}
    )
    assert registration.status_code == status.HTTP_201_CREATED, registration.content
    device = JsonAPIClient()
    device.credentials(HTTP_AUTHORIZATION="Bearer " + str(registration.json()["token"]))
    assert device.get(PREFS_URL).status_code == status.HTTP_200_OK
    assert (
        device.put(
            PREFS_URL,
            {"preferences": [{"event_type": "in_human_review", "enabled": True}]},
            format="json",
        ).status_code
        == status.HTTP_200_OK
    )

    # Agent token: denied on both verbs with the catalog code.
    token = issue_agent_token(owner_client, project.pk, "coder")
    agent = agent_client(token)
    denied_get = agent.get(PREFS_URL)
    assert denied_get.status_code == status.HTTP_403_FORBIDDEN
    assert denied_get.json()["error"]["code"] == "ROLE_NOT_PERMITTED"
    denied_put = agent.put(
        PREFS_URL,
        {"preferences": [{"event_type": "in_human_review", "enabled": True}]},
        format="json",
    )
    assert denied_put.status_code == status.HTTP_403_FORBIDDEN

    # Anonymous: AUTH_REQUIRED (401), catalog-closed.
    anonymous = APIClient()
    response = anonymous.get(PREFS_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


# --- trigger → preference-key mapping (the recorded ruling) ------------------


@pytest.mark.parametrize(
    ("trigger", "expected"),
    [
        ({"event_type": "task.transitioned", "reason_code": "retry_exhausted"}, "retry_exhaustion"),
        ({"event_type": "task.transitioned", "reason_code": "audit_escalated"}, "in_human_review"),
        ({"event_type": "task.transitioned", "reason_code": "scope_violation"}, "in_human_review"),
        ({"event_type": "merge.failed", "reason_code": "merge_failed"}, "merge_failure"),
        ({"event_type": "merge_failed", "reason_code": "merge_conflict"}, "merge_failure"),
        ({}, "in_human_review"),  # unknown → the umbrella, never the digest
    ],
)
def test_every_trigger_resolves_to_exactly_one_preference_key(
    trigger: dict[str, Any], expected: str
) -> None:
    """Section 9.8's four triggers map disjointly — isolation by construction."""
    assert resolve_preference_key(trigger) == expected
    assert resolve_preference_key(trigger) != "completion_digest"


# --- dispatch consultation (AC 2; ordering risk note) -----------------------


def test_disabled_type_makes_zero_fcm_attempts_and_records_nothing(
    owner_client: JsonAPIClient, task: Task, devices: tuple[Device, Device]
) -> None:
    """Disabled → no sender call, no dedupe claim, no tracking row."""
    _set(owner_client, "in_human_review", False)
    transport = FakeTransport()
    set_fcm_transport(transport)

    summary = dispatch_module.dispatch_push(_trigger(task))

    assert summary == {
        "accepted": 0,
        "transient_failed": 0,
        "permanent_failed": 0,
        "suppressed": 2,  # both active devices — counted, never contacted
    }
    assert transport.calls == []
    assert PushDeliveryRecord.objects.count() == 0  # Section 17 metric: untouched
    assert PushDedupeRecord.objects.count() == 0  # consultation runs before dedupe


def test_disabling_one_type_leaves_the_others_unaffected(
    owner_client: JsonAPIClient, task: Task, devices: tuple[Device, Device]
) -> None:
    """Per-event isolation: the umbrella off, the specific types still send."""
    _set(owner_client, "in_human_review", False)
    transport = FakeTransport()
    set_fcm_transport(transport)

    merge = dispatch_module.dispatch_push(
        _trigger(task, event_type="merge.failed", reason_code="merge_failed", state_version=4)
    )
    retry = dispatch_module.dispatch_push(
        _trigger(task, reason_code="retry_exhausted", state_version=5)
    )

    assert merge["accepted"] == 2
    assert retry["accepted"] == 2
    assert len(transport.calls) == 4  # two devices per enabled trigger


def test_retry_exhaustion_toggle_governs_only_the_retry_trigger(
    owner_client: JsonAPIClient, task: Task, devices: tuple[Device, Device]
) -> None:
    """T9's reason flips its own key; a generic escalation keeps flowing."""
    _set(owner_client, "retry_exhaustion", False)
    transport = FakeTransport()
    set_fcm_transport(transport)

    muted = dispatch_module.dispatch_push(
        _trigger(task, reason_code="retry_exhausted", state_version=3)
    )
    assert muted["suppressed"] == 2
    assert transport.calls == []

    flowing = dispatch_module.dispatch_push(_trigger(task, state_version=4))
    assert flowing["accepted"] == 2
    assert len(transport.calls) == 2


def test_re_enabling_notifies_future_events_only(
    owner_client: JsonAPIClient, task: Task, devices: tuple[Device, Device]
) -> None:
    """No queue: re-enabling fires nothing by itself; only new events send."""
    _set(owner_client, "in_human_review", False)
    transport = FakeTransport()
    set_fcm_transport(transport)

    suppressed = dispatch_module.dispatch_push(_trigger(task, state_version=3))
    assert suppressed["suppressed"] == 2
    assert transport.calls == []

    _set(owner_client, "in_human_review", True)  # nothing replays here
    assert transport.calls == []

    future = dispatch_module.dispatch_push(_trigger(task, state_version=4))
    assert future["accepted"] == 2
    assert len(transport.calls) == 2


def test_preference_suppression_never_enters_the_dedupe_or_tracking_tables(
    owner_client: JsonAPIClient, task: Task, devices: tuple[Device, Device]
) -> None:
    """The ordering AC: consultation strictly precedes dedupe and send."""
    _set(owner_client, "in_human_review", False)
    set_fcm_transport(FakeTransport())

    dispatch_module.dispatch_push(_trigger(task, state_version=3))
    assert PushDedupeRecord.objects.count() == 0
    assert PushDeliveryRecord.objects.count() == 0

    # Recorded reading (WP-5.4 changelog): because the key was never
    # claimed, a *re-dispatch* of that never-delivered event after
    # re-enabling delivers once — re-enabling itself fires nothing
    # (asserted above), and there is nothing stored to replay.
    _set(owner_client, "in_human_review", True)
    replayed = dispatch_module.dispatch_push(_trigger(task, state_version=3))
    assert replayed["accepted"] == 2
    assert PushDeliveryRecord.objects.count() == 2


def test_digest_is_stored_but_never_consulted_by_dispatch(task: Task) -> None:
    """OQ-13 keeps the digest unbuilt — no trigger can select its key."""
    for trigger in (
        _trigger(task),
        _trigger(task, event_type="merge.failed", reason_code="merge_failed"),
        _trigger(task, reason_code="retry_exhausted"),
    ):
        assert resolve_preference_key(trigger) != "completion_digest"
