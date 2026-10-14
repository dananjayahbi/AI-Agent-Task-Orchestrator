"""MT-1.15-03 — the NFR-12 idempotency suite on **real Postgres** (Section 18).

One gate for the four operation classes NFR-12 names — claim,
checkpoint, submit, decision — each proven by duplicate sequential and
concurrent replay. Consolidation, not duplication (Section 19.6): this
module adds the PG-layer proofs that did not exist and drives them
through the shared duplicate-request driver extracted from MT-1.6-08's
harness (``tests.integration.race_harness``); classes with existing
coverage are adopted by reference, never re-implemented.

Coverage map (what proves what — nothing below is re-implemented):

* **claim** — adopted from ``test_claim_race_postgres.py`` (same gate):
  the 50-attempt same-session service storm (one lease, one event, no
  listener noise), the 50-attempt endpoint race (one 200 / 49
  ``TASK_ALREADY_CLAIMED``), the same-``Idempotency-Key`` endpoint race
  with byte-identical replays, and the sequential-claims control; the
  unit layer's sequential claim replays stay in
  ``test_claim_release_endpoints.py``.
* **checkpoint** — this file: sequential same-key replay (one row, one
  extension, byte-identical outcome, one event) and the concurrent
  same-key storm's persistence invariants (one row + one event per
  executed request, lease capped, no transitions, sequential retry
  replays without a further write).
* **submit** — this file: sequential same-key replay (one resolution,
  one transition, one event, one stored patch) and the concurrent
  same-key storm (one 201 body or a catalog ``TASK_STATE_CONFLICT`` 409
  — never a second completion side effect; the Section 9.1 repeat-submit
  reading is recorded in the WP changelog).
* **decision** — landed with WP-3.6: the review endpoint's sequential
  and concurrent same-key replays (plus the MT-3.6-04 races) now live
  in ``test_review_decision_postgres.py`` — adopted there, never
  re-implemented here (the deferral this bullet used to carry is
  closed by that file).

Skipped automatically outside the integration layer or when Postgres is
unreachable — the skip reason carries the exact command:

    uv run --directory backend pytest tests/integration --ds apps.core.settings.dev
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.core.errors import TASK_STATE_CONFLICT
from apps.events.models import Event, EventType
from apps.projects.models import Project
from apps.tasks.models import (
    TaskArtifact,
    TaskCheckpoint,
    TaskResolution,
    TaskState,
    TaskTransition,
)
from tests.integration.race_harness import duplicate_posts, skip_reason
from tests.test_checkpoint_endpoint import checkpoint_body  # adopted factory, not copied
from tests.wp32_helpers import (  # noqa: F401  (autouse fixtures promoted)
    _code,
    active_policy_project,
    agent_client,
    claimed_task,
    clean_throttle_cache,
    issue_agent_token,
    local_storage,
    login_owner,
    restore_submission_registry,
    submission_body,
)

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(skip_reason() is not None, reason=skip_reason() or "unreachable"),
]


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (cookie transport) for token minting."""
    return login_owner()


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


def _coder(owner_client: APIClient, project: Project) -> APIClient:
    """A coder-agent client scoped to the project."""
    return agent_client(issue_agent_token(owner_client, project.pk, "coder"))


def _stored_patch_files() -> int:
    """Files under the per-test ``MEDIA_ROOT`` (storage-side effect count)."""
    return len([entry for entry in Path(settings.MEDIA_ROOT).rglob("*") if entry.is_file()])


# --- checkpoint: sequential + concurrent duplicate replay --------------------


def test_checkpoint_sequential_same_key_replay_stores_one_row_one_event(
    owner_client: APIClient, project: Project
) -> None:
    """NFR-12 checkpoint, sequential: the replay is the stored outcome."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1)
    path = f"/api/v1/tasks/{task.pk}/checkpoints"
    body = checkpoint_body(session_id="sess_wp32")

    first = agent.post(path, body, format="json", HTTP_IDEMPOTENCY_KEY="wp115-ckpt-seq")
    assert first.status_code == 200, first.content
    task.refresh_from_db()
    extended_expiry = task.lease_expires_at

    second = agent.post(path, body, format="json", HTTP_IDEMPOTENCY_KEY="wp115-ckpt-seq")

    assert second.status_code == 200
    assert second.json() == first.json(), "the replay is the stored outcome"
    assert TaskCheckpoint.objects.filter(task=task).count() == 1, "no duplicate row"
    task.refresh_from_db()
    assert task.lease_expires_at == extended_expiry, "no double extension"
    assert task.state == TaskState.IN_PROGRESS, "no state regression"
    # Exactly one domain event per logical operation (Section 9.6), and
    # no orphaned rows — history still matches events one-to-one.
    assert Event.objects.filter(task_id=task.pk, type=EventType.TASK_CHECKPOINT).count() == 1
    assert Event.objects.filter(task_id=task.pk, type=EventType.TASK_CLAIMED).count() == 1
    assert TaskTransition.objects.filter(task=task).count() == 1, "checkpoints never transition"


def test_checkpoint_concurrent_same_key_duplicates_keep_persistence_invariants(
    owner_client: APIClient, project: Project
) -> None:
    """NFR-12 checkpoint, concurrent: one row + one event per execution.

    Six identical keyed POSTs race on the row lock. What the architecture
    guarantees under concurrency is asserted here: every response is 2xx,
    each *executed* request stored exactly one row and one event (replays
    add neither — distinct outcome bodies == row count), the task never
    regresses, the lease never breaches the Section 8.6 cap, and a
    sequential retry after the storm replays byte-identically with no
    further write. The cache store itself does not linearize concurrent
    pre-store executions — recorded as a finding + OQ in the WP-1.15
    changelog per MT-1.15-03's out-of-scope (mechanism changes are
    follow-ups; this task consolidates proof).
    """
    token = issue_agent_token(owner_client, project.pk, "coder")
    agent = agent_client(token)
    task = claimed_task(project, 1)
    path = f"/api/v1/tasks/{task.pk}/checkpoints"
    body = checkpoint_body(session_id="sess_wp32")
    headers = {
        "Authorization": "Bearer " + str(token["token"]),
        "Idempotency-Key": "wp115-ckpt-race",
    }

    responses = duplicate_posts(6, path, body, headers=headers, join_timeout=120)

    statuses = [response.status_code for response in responses]
    assert statuses == [200] * 6, f"a repeated checkpoint is always legal: {statuses}"
    bodies = [response.json() for response in responses]
    distinct = {json.dumps(single, sort_keys=True) for single in bodies}
    rows = TaskCheckpoint.objects.filter(task=task).count()
    assert 1 <= rows <= len(responses)
    assert len(distinct) == rows, "one distinct outcome per executed request; replays duplicate"

    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS, "no state regression"
    assert task.worker_session_id == "sess_wp32"
    assert task.lease_acquired_at is not None
    assert task.lease_expires_at is not None
    cap = task.lease_acquired_at + timedelta(minutes=project.agent_policy.lease_max_total_minutes)
    assert task.lease_expires_at <= cap, "Section 8.6 cap holds however many duplicates ran"
    # One event per stored row; checkpoints dispatch no transition, so
    # the append-only history is untouched (no double state transition).
    assert Event.objects.filter(task_id=task.pk, type=EventType.TASK_CHECKPOINT).count() == rows
    assert TaskTransition.objects.filter(task=task).count() == 1, "only the claim's T4"

    # Sequential retry after the storm: replay, no further write (NFR-12).
    retry = agent.post(path, body, format="json", HTTP_IDEMPOTENCY_KEY="wp115-ckpt-race")
    assert retry.status_code == 200
    assert json.dumps(retry.json(), sort_keys=True) in distinct
    assert TaskCheckpoint.objects.filter(task=task).count() == rows
    assert Event.objects.filter(task_id=task.pk, type=EventType.TASK_CHECKPOINT).count() == rows


# --- submit: sequential + concurrent duplicate replay ------------------------


def test_submit_sequential_same_key_replay_stores_one_resolution_and_transition(
    owner_client: APIClient, project: Project
) -> None:
    """NFR-12 submit, sequential: replay = stored 201, one single effect."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])
    path = f"/api/v1/tasks/{task.pk}/resolution"
    body = submission_body()

    first = agent.post(path, body, format="json", HTTP_IDEMPOTENCY_KEY="wp115-submit-seq")
    assert first.status_code == 201, first.content
    second = agent.post(path, body, format="json", HTTP_IDEMPOTENCY_KEY="wp115-submit-seq")

    assert second.status_code == 201
    assert second.json() == first.json(), "the replay is the stored outcome"
    task.refresh_from_db()
    assert task.state == TaskState.TO_BE_AUDITED, "one transition to the Section 9.1 target"
    assert task.worker_agent_id is None, "invariant 1 holds after the replay"
    assert TaskResolution.objects.filter(task=task).count() == 1
    assert TaskArtifact.objects.filter(resolution__task=task, kind="patch").count() == 1
    assert _stored_patch_files() == 1, "storage side stays single-effect too"
    assert (
        TaskTransition.objects.filter(task=task, from_state=TaskState.IN_PROGRESS).count() == 1
    ), "one submission transition, never a T7 double-fire"
    assert Event.objects.filter(task_id=task.pk, type=EventType.TASK_TRANSITIONED).count() == 1
    assert Event.objects.filter(task_id=task.pk, type=EventType.TASK_CLAIMED).count() == 1


def test_submit_concurrent_same_key_duplicates_stay_single_effect(
    owner_client: APIClient, project: Project
) -> None:
    """NFR-12 submit, concurrent: one 201 body or a catalog 409 — never twice.

    Six identical keyed POSTs race on the task row lock: the state
    machine admits exactly one completion (T7), a re-execution answers
    ``TASK_STATE_CONFLICT``, and a request that finds the stored outcome
    replays it byte-identically — every path free of a second completion
    side effect (the Section 9.1 repeat-submit reading recorded in the
    changelog). Both the row layer and the storage layer stay single.
    """
    token = issue_agent_token(owner_client, project.pk, "coder")
    agent = agent_client(token)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])
    path = f"/api/v1/tasks/{task.pk}/resolution"
    body = submission_body()
    headers = {
        "Authorization": "Bearer " + str(token["token"]),
        "Idempotency-Key": "wp115-submit-race",
    }

    responses = duplicate_posts(6, path, body, headers=headers, join_timeout=120)

    statuses = [response.status_code for response in responses]
    assert set(statuses) <= {201, 409}, f"no 400/500 leaks in the storm: {statuses}"
    assert 201 in statuses, statuses
    won = [response.json() for response in responses if response.status_code == 201]
    assert all(single == won[0] for single in won), "one execution; every replay identical"
    for response in responses:
        if response.status_code == 409:
            assert _code(response) == TASK_STATE_CONFLICT, "Section 9.2 catalog only"

    task.refresh_from_db()
    assert task.state == TaskState.TO_BE_AUDITED
    assert task.worker_agent_id is None, "invariant 1: no lease outside in_progress"
    assert TaskResolution.objects.filter(task=task).count() == 1
    assert TaskArtifact.objects.filter(resolution__task=task, kind="patch").count() == 1
    assert _stored_patch_files() == 1, "storage side stays single-effect too"
    assert (
        TaskTransition.objects.filter(task=task, from_state=TaskState.IN_PROGRESS).count() == 1
    ), "one submission transition, never a T7 double-fire"
    assert Event.objects.filter(task_id=task.pk, type=EventType.TASK_TRANSITIONED).count() == 1
    assert Event.objects.filter(task_id=task.pk, type=EventType.TASK_CLAIMED).count() == 1

    # Sequential retry after the storm: stored 201, nothing new (NFR-12).
    retry = agent.post(path, body, format="json", HTTP_IDEMPOTENCY_KEY="wp115-submit-race")
    assert retry.status_code == 201
    assert retry.json() == won[0]
    assert TaskResolution.objects.filter(task=task).count() == 1
