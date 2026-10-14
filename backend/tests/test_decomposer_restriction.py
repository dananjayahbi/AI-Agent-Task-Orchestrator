"""MT-3.8-03 — the decomposer restriction suite (Section 12.2 walked).

UC-10 / G-19 / Sections 8.2 (T2, T4, T11), 10.5, 19, 20.4, 20.5: one
asserting test per **No** cell of the Section 12.2 Decomposer column,
against the real routes with a real ``decomposer``-scoped agent token:

* **Manage projects/policy** — ``PATCH /projects/{pid}`` and
  ``PATCH /projects/{pid}/policy`` answer ``ROLE_NOT_PERMITTED`` (the
  policy *read* cell is §9.2's agent read — manage is the Owner write);
* **Publish tasks** — ``CanPublishTasks`` refuses the decomposer (T2;
  no HTTP route has landed yet, so the suite mounts the same permission
  class the authorization matrix probes, at a module-local route —
  **T3 unpublish shares the owner draft⇄pending cell**: there is no
  separate unpublish permission class in the catalog and none is
  invented here);
* **Claim ``pending``** (T4) / **Claim ``to_be_audited``** (T11) — both
  403 with the catalog code, rows untouched;
* **Submit resolution** / **Submit verdict** — 403 with the catalog
  code;
* **Review decisions** (T15/T16 entry) — 403 with the catalog code;
* **Merge queue** — ``GET /merge/pending`` *and*
  ``POST /merge/{task}/start`` both 403 (read + start are the row);
* **Read events** — 403 with the catalog code;

plus the two scope extras: the positive control (**Create draft tasks**
— 201, ``draft``, ``task.created``) and **work listing** (§10.5 has no
decomposer listing role: ``role=decomposer`` is rejected, and every
offer a decomposer *can* see is refused on claim — no claimable work).

Regression controls ride in the same run: the Owner publish probe, a
coder claim of ``pending`` and an auditor claim of ``to_be_audited``
all still succeed — the denials are role-scoped, never global.

Run with ``pytest backend/tests -k decomposer_restriction -q``.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import override_settings
from django.urls import path as url_path
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanPublishTasks
from apps.projects.models import Project
from apps.tasks.models import Task, TaskState

from .wp15_helpers import make_project, make_task
from .wp16_helpers import restore_lease_registry  # noqa: F401  (autouse)
from .wp33_helpers import (  # noqa: F401  (autouse: registry restore)
    JsonAPIClient,
    agent_client,
    auditable_task,
    claim_as_auditor,
    issue_agent_token,
    login_owner_client,
    restore_audit_registry,
)

pytestmark = pytest.mark.django_db

CREATE_URL = "/api/v1/projects/{pid}/tasks"
CLAIM_URL = "/api/v1/tasks/{task_id}/claim"
RESOLUTION_URL = "/api/v1/tasks/{task_id}/resolution"
VERDICT_URL = "/api/v1/tasks/{task_id}/audit-verdict"
REVIEW_URL = "/api/v1/tasks/{task_id}/review"
WORK_URL = "/api/v1/projects/{pid}/work"
PROJECT_URL = "/api/v1/projects/{pid}"
POLICY_URL = "/api/v1/projects/{pid}/policy"
EVENTS_URL = "/api/v1/events"
MERGE_PENDING_URL = "/api/v1/merge/pending"
MERGE_START_URL = "/api/v1/merge/{task_id}/start"

DENIED_CODE = "ROLE_NOT_PERMITTED"

_PUBLISH = "/probe/publish"


class _PublishProbeView(APIView):
    """The **Publish tasks** cell's real permission class (matrix probe)."""

    permission_classes: list[type[BasePermission]] = [CanPublishTasks]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """200 = this actor's Section 12.2 cell permits publish (T2)."""
        return Response({"ok": True})


# Module-local routes for the probe test only (``override_settings`` scopes
# the replacement urlconf to that test — every other test below runs on the
# real ``config.urls``).
urlpatterns = [
    url_path(_PUBLISH.lstrip("/"), _PublishProbeView.as_view(), name="g2-publish-probe"),
]


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    return login_owner_client()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the restriction suite."""
    return make_project(name="WP-3.8 decomposer restriction")


def _decomposer(owner_client: JsonAPIClient, project: Project) -> JsonAPIClient:
    """A project-scoped agent token carrying only the decomposer role."""
    token = issue_agent_token(owner_client, project.pk, "decomposer")
    return agent_client(token)


@pytest.fixture
def decomposer(owner_client: JsonAPIClient, project: Project) -> JsonAPIClient:
    """Minted at fixture time — before any urlconf override is active.

    The token route lives in ``config.urls``, so the probe test (which
    swaps ROOT_URLCONF for its body) must receive its client already built.
    """
    return _decomposer(owner_client, project)


def _code(response: Any) -> str:
    """The catalog code of one standard Section 9.2 envelope."""
    error = response.json()["error"]
    assert error["code"] in {
        "AUTH_REQUIRED",
        "AUTH_FORBIDDEN_PROJECT",
        "ROLE_NOT_PERMITTED",
        "VALIDATION_ERROR",
        "TASK_STATE_CONFLICT",
        "TASK_ALREADY_CLAIMED",
    }
    return str(error["code"])


def _assert_denied(response: Any) -> None:
    """One 403 carrying the closed-catalog refusal code."""
    assert response.status_code == 403, response.content
    assert _code(response) == DENIED_CODE


# --- positive control: the one Yes cell ---------------------------------------


def test_decomposer_restriction_create_draft_still_succeeds(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """The Yes cell stays open: 201, ``draft``, ``task.created`` (T1)."""
    response = _decomposer(owner_client, project).post(
        CREATE_URL.format(pid=project.pk),
        {"title": "Split the billing module", "description": "Decomposition slice."},
        format="json",
    )
    assert response.status_code == 201, response.content
    payload = response.json()
    assert payload["state"] == TaskState.DRAFT
    from apps.events.models import Event

    assert Event.objects.filter(task_id=payload["id"], type="task.created").exists()


# --- Manage projects/policy: No ------------------------------------------------


def test_decomposer_restriction_cannot_manage_projects_or_policy(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Section 12.2 row 1: project PATCH and policy PATCH are Owner-only."""
    decomposer = _decomposer(owner_client, project)

    response = decomposer.patch(
        PROJECT_URL.format(pid=project.pk),
        {"name": "renamed", "version": 1},
        format="json",
    )
    _assert_denied(response)

    response = decomposer.patch(
        POLICY_URL.format(pid=project.pk),
        {"max_concurrent_tasks": 9},
        format="json",
    )
    _assert_denied(response)

    project.refresh_from_db()
    assert project.name == "WP-3.8 decomposer restriction"


# --- Publish tasks: No (T2/T3 owner flow) -------------------------------------


@override_settings(ROOT_URLCONF=__name__)
def test_decomposer_restriction_cannot_publish_or_unpublish(
    decomposer: JsonAPIClient, owner_client: JsonAPIClient
) -> None:
    """T2/T3 gate: ``CanPublishTasks`` refuses decomposers, admits Owner.

    There is no HTTP publish route yet (the service owns T2/T3), so this
    suite mounts the real permission class exactly as the authorization
    matrix does — the class any future route must keep. T3 rides the same
    class: the catalog has no unpublish permission and none is invented.
    """
    _assert_denied(decomposer.post(_PUBLISH, {}, format="json"))

    # Role-scoped, not globally broken: the Owner cell still answers 200.
    assert owner_client.post(_PUBLISH, {}, format="json").status_code == 200


# --- Claim pending (T4) and Claim to_be_audited (T11): No ---------------------


def test_decomposer_restriction_cannot_claim_pending_or_to_be_audited(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Both claim cells refuse the decomposer; no row moves."""
    decomposer = _decomposer(owner_client, project)
    pending = make_task(project, 1, state=TaskState.PENDING)
    audited = make_task(project, 2, state=TaskState.TO_BE_AUDITED, attempt_number=1)

    response = decomposer.post(
        CLAIM_URL.format(task_id=pending.pk),
        {"session_id": "sess-g2-decomposer", "worker_agent_id": "g2-decomposer"},
        format="json",
    )
    _assert_denied(response)

    response = decomposer.post(
        CLAIM_URL.format(task_id=audited.pk),
        {
            "session_id": "sess-g2-decomposer",
            "worker_agent_id": "g2-decomposer",
            "role": "auditor",
        },
        format="json",
    )
    _assert_denied(response)

    for task in (pending, audited):
        task.refresh_from_db()
        assert task.version == 1, task.pk
        assert task.worker_session_id is None
    assert Task.objects.filter(pk=pending.pk, state=TaskState.PENDING).exists()


# --- Submit resolution / Submit verdict: No -----------------------------------


def test_decomposer_restriction_cannot_submit_resolution_or_verdict(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Both agent write cells refuse the decomposer with the catalog code."""
    decomposer = _decomposer(owner_client, project)
    pending = make_task(project, 3, state=TaskState.PENDING)
    audited = make_task(project, 4, state=TaskState.TO_BE_AUDITED, attempt_number=1)

    response = decomposer.post(
        RESOLUTION_URL.format(task_id=pending.pk),
        {
            "session_id": "sess-g2-decomposer",
            "lease_generation": 1,
            "git_branch": "feat/g2-decomposer",
            "commit_sha": "0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
            "execution_summary": "must never land",
            "patch": "",
        },
        format="json",
    )
    _assert_denied(response)

    response = decomposer.post(
        VERDICT_URL.format(task_id=audited.pk),
        {
            "session_id": "sess-g2-decomposer",
            "lease_generation": 1,
            "task_id": audited.pk,
            "verdict": "pass",
            "confidence": 5,
            "evidence": {"commands": [{"label": "t", "command": "pytest -q", "exit_code": 0}]},
        },
        format="json",
    )
    _assert_denied(response)

    for task in (pending, audited):
        task.refresh_from_db()
        assert task.version == 1, task.pk


# --- Review decisions: No -----------------------------------------------------


def test_decomposer_restriction_cannot_take_a_review_decision(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T15/T16 entry: the review route refuses the decomposer."""
    decomposer = _decomposer(owner_client, project)
    reviewing = make_task(project, 5, state=TaskState.IN_HUMAN_REVIEW)

    response = decomposer.post(
        REVIEW_URL.format(task_id=reviewing.pk),
        {"decision": "reassign", "version": reviewing.version},
        format="json",
    )
    _assert_denied(response)

    reviewing.refresh_from_db()
    assert reviewing.state == TaskState.IN_HUMAN_REVIEW
    assert reviewing.version == 1


# --- Merge queue: No (read + start) -------------------------------------------


def test_decomposer_restriction_cannot_read_or_start_the_merge_queue(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """The whole row refuses: ``GET /merge/pending`` and start both 403."""
    decomposer = _decomposer(owner_client, project)
    reviewing = make_task(project, 6, state=TaskState.IN_HUMAN_REVIEW)

    _assert_denied(decomposer.get(MERGE_PENDING_URL))
    _assert_denied(
        decomposer.post(
            MERGE_START_URL.format(task_id=reviewing.pk),
            {"idempotency_key": "g2-restriction-start"},
            format="json",
        )
    )

    reviewing.refresh_from_db()
    assert reviewing.state == TaskState.IN_HUMAN_REVIEW
    assert reviewing.merge_status == "none", "a refused start never queues a merge"


# --- Read events: No ----------------------------------------------------------


def test_decomposer_restriction_cannot_read_events(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Event history is the Owner dashboard's surface — agents never read it."""
    decomposer = _decomposer(owner_client, project)
    _assert_denied(decomposer.get(EVENTS_URL))

    # Role-scoped: the Owner cell still answers 200 in the same run.
    assert owner_client.get(EVENTS_URL).status_code == 200


# --- Work listing: no decomposer listing role, no claimable work --------------


def test_decomposer_restriction_work_listing_offers_nothing_claimable(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """§10.5 roles are coder/auditor: a decomposer never obtains claimable work.

    The offer endpoint itself is an agent surface (IsAgentToken), so the
    decomposer can *read* it — but ``role=decomposer`` is not a listing
    role (400), and every row the default coder listing does show is
    refused on claim by the T4 cell above: nothing is claimable.
    """
    decomposer = _decomposer(owner_client, project)
    pending = make_task(project, 7, state=TaskState.PENDING)

    invalid = decomposer.get(WORK_URL.format(pid=project.pk), {"role": "decomposer"})
    assert invalid.status_code == 400, invalid.content
    assert _code(invalid) == "VALIDATION_ERROR"

    offers = decomposer.get(WORK_URL.format(pid=project.pk), {"role": "coder"})
    assert offers.status_code == 200, offers.content
    assert pending.pk in {row["id"] for row in offers.json()["results"]}

    claim = decomposer.post(
        CLAIM_URL.format(task_id=pending.pk),
        {"session_id": "sess-g2-decomposer", "worker_agent_id": "g2-decomposer"},
        format="json",
    )
    _assert_denied(claim)


# --- regression controls: the other cells keep succeeding in the same run -----


def test_decomposer_restriction_role_scoped_controls_still_succeed(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Coder claim of ``pending`` and auditor claim of ``to_be_audited`` pass.

    Paired with the Owner ``200`` in the publish probe and the draft
    positive control, every denial above is proven role-scoped.
    """
    coder_token = issue_agent_token(owner_client, project.pk, "coder")
    coder = agent_client(coder_token)
    pending = make_task(project, 8, state=TaskState.PENDING)
    claim = coder.post(
        CLAIM_URL.format(task_id=pending.pk),
        {"session_id": "sess-g2-coder", "worker_agent_id": "g2-coder"},
        format="json",
    )
    assert claim.status_code == 200, claim.content
    pending.refresh_from_db()
    assert pending.state == TaskState.IN_PROGRESS
    assert pending.worker_session_id == "sess-g2-coder"

    auditor_token = issue_agent_token(owner_client, project.pk, "auditor")
    auditor = agent_client(auditor_token)
    audited = auditable_task(project, 9)
    takeover = claim_as_auditor(auditor, audited.pk)
    assert takeover.status_code == 200, takeover.content
    audited.refresh_from_db()
    assert audited.state == TaskState.TO_BE_AUDITED
    assert audited.worker_session_id == "sess_wp33_auditor"
