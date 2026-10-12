"""MT-1.9-01 — the Event model: envelope fields, monotonic id, replay order.

Covers the MT's acceptance points that belong to the model itself:

* the field set is **exactly** the Section 9.6 envelope plus the
  Section 12.5 correlation id — nothing added, dropped or renamed
  (Section 20.5);
* the envelope projection re-groups ``actor_type``/``actor_ref`` into the
  structured ``{"type", "ref"}`` object and uses ``id`` as the SSE event
  id (Section 9.6);
* ``occurred_at`` is recorded at write time, inside the open
  transaction, and never moves afterwards (append-only);
* ids under concurrent inserts are strictly increasing per writer and
  never repeat — the monotonicity guarantee (Section 9.6);
* reading by ``id`` yields a total order usable for replay
  (MT-1.10-03 input);
* the closed catalogs hold at the database (CheckConstraint) and the
  ORM refuses every mutation door (Section 12.5).

The database-level INSERT/UPDATE/DELETE privilege half lives in
``test_insert_only_permissions.py`` (MT-1.9-04).
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest
from django.db import IntegrityError, OperationalError, connection, transaction
from django.utils import timezone

from apps.events.envelope import event_envelope
from apps.events.models import Event, EventImmutable

# MT-1.9-01 acceptance: exactly the Section 9.6 envelope fields
# (id, type, project_id, task_id, occurred_at, actor) plus Section 12.5's
# correlation id — the structured actor is stored in the Section 7.2
# actor_type/actor_ref column pair, not as a flattened string.
MODEL_FIELDS = frozenset(
    {
        "id",
        "type",
        "project_id",
        "task_id",
        "occurred_at",
        "actor_type",
        "actor_ref",
        "data",
        "correlation_id",
    }
)


def _write(**overrides: Any) -> Event:
    """One event row with canonical defaults (test fixture, not product code)."""
    payload: dict[str, Any] = {
        "type": "task.transitioned",
        "project_id": "PID00001",
        "task_id": "PID00001-T001",
        "occurred_at": timezone.now(),
        "actor_type": "owner",
        "actor_ref": "user:1",
        "data": {"from_state": "draft", "to_state": "pending"},
        "correlation_id": "corr-test-0001",
    }
    payload.update(overrides)
    created: Event = Event.objects.create(**payload)
    return created


def test_model_carries_exactly_the_envelope_fields_plus_correlation(db: None) -> None:
    """Section 9.6 envelope + Section 12.5 correlation id — no other column."""
    assert {field.name for field in Event._meta.fields} == MODEL_FIELDS


def test_envelope_is_the_exact_section_9_6_object_with_the_sse_id(db: None) -> None:
    """The wire shape: seven keys, structured actor, ``id`` as the SSE id."""
    event = _write()

    envelope = event_envelope(event)

    assert set(envelope) == {
        "id",
        "type",
        "project_id",
        "task_id",
        "occurred_at",
        "actor",
        "data",
    }
    assert envelope["id"] == event.pk, "Section 9.6: the SSE id *is* the row id"
    assert envelope["type"] == "task.transitioned"
    assert envelope["actor"] == {"type": "owner", "ref": "user:1"}, "never flattened"
    assert envelope["data"] == {"from_state": "draft", "to_state": "pending"}
    assert envelope["occurred_at"].endswith("Z"), "plan example renders UTC with Z"


def test_occurred_at_is_recorded_at_write_time_inside_the_transaction(
    db: None,
) -> None:
    """Principle P7: the server clock stamps the row while the txn is open."""
    before = timezone.now()
    with transaction.atomic():
        event = _write()
        inside = timezone.now()
    after = timezone.now()

    assert before <= event.occurred_at <= inside
    assert event.occurred_at <= after
    # ...and an append-only row never re-stamps: the stored value is identical.
    stored = Event.objects.get(pk=event.pk)
    assert stored.occurred_at == event.occurred_at


def test_database_refuses_any_type_outside_the_section_9_6_catalog(
    db: None,
) -> None:
    """The closed 24-type catalog is a CheckConstraint, not just app checks."""
    with pytest.raises(IntegrityError), transaction.atomic():
        _write(type="token.issued")  # no catalog type exists for token actions

    assert Event.objects.count() == 0


def test_database_refuses_a_non_canonical_actor(db: None) -> None:
    """``actor.type`` is the Section 7.2 triad at the database too."""
    with pytest.raises(IntegrityError), transaction.atomic():
        _write(actor_type="robot")

    assert Event.objects.count() == 0


def test_reading_by_id_yields_a_total_order_for_replay(db: None) -> None:
    """Ordering by ``id`` is total and gap-tolerant (MT-1.10-03 input)."""
    written = [_write(data={"n": n}) for n in range(5)]

    replayed = list(Event.objects.order_by("id"))

    ids = [event.pk for event in replayed]
    assert len(ids) == 5
    assert ids == sorted(ids), "id order is a total order"
    assert len(set(ids)) == 5, "ids never repeat"
    assert [event.data["n"] for event in replayed] == [0, 1, 2, 3, 4]
    assert ids == [event.pk for event in written], "insertion order == id order here"


def test_orm_refuses_every_mutation_door(db: None) -> None:
    """Section 12.5 at the model layer: no save/delete/update path survives."""
    event = _write()

    event.type = "project.updated"
    with pytest.raises(EventImmutable):
        event.save()
    with pytest.raises(EventImmutable):
        event.delete()
    with pytest.raises(EventImmutable):
        Event.objects.update(type="project.updated")
    with pytest.raises(EventImmutable):
        Event.objects.filter(pk=event.pk).update(type="project.updated")
    with pytest.raises(EventImmutable):
        Event.objects.bulk_update([event], ["type"])
    with pytest.raises(EventImmutable):
        Event.objects.all().delete()

    stored = Event.objects.get(pk=event.pk)
    assert stored.type == "task.transitioned", "the row never moved"


@pytest.mark.django_db(transaction=True)
def test_concurrent_inserts_produce_strictly_increasing_unique_ids() -> None:
    """The monotonic-id guarantee under concurrency (MT-1.9-01 acceptance).

    Barrier-synchronized threads insert through the shared in-memory
    SQLite database; SQLite's ``database is locked`` errors are absorbed
    by a time-bounded retry loop (the id-allocation suite's pattern).
    Asserted: every id unique, each writer's ids strictly increasing,
    and reading back in ``id`` order returns every row — a total order,
    with gaps allowed (Section 9.6 resume guarantees concern delivery,
    not contiguous ids — MT-1.9-01 risk note).
    """
    threads, per_thread = 8, 10
    barrier = threading.Barrier(threads, timeout=30)
    collected: dict[int, list[int]] = {}
    failures: list[str] = []
    collect_lock = threading.Lock()
    retry_deadline = time.monotonic() + 30

    def insert_with_retry() -> int:
        delay = 0.001
        while time.monotonic() < retry_deadline:
            try:
                event = _write(task_id=None, correlation_id=f"corr-{threading.get_ident()}")
                identifier = event.pk
                assert identifier is not None
                return identifier
            except OperationalError:
                time.sleep(delay)
                delay = min(delay * 2, 0.02)
        raise AssertionError("insert never got past the database lock within 30s")

    def worker(index: int) -> None:
        try:
            barrier.wait()
            ids: list[int] = []
            for _ in range(per_thread):
                ids.append(insert_with_retry())
            with collect_lock:
                collected[index] = ids
        except Exception as exc:  # noqa: BLE001 - surfaced to the main thread
            with collect_lock:
                failures.append(repr(exc))
        finally:
            connection.close()

    workers = [threading.Thread(target=worker, args=(index,)) for index in range(threads)]
    for thread in workers:
        thread.start()
    for thread in workers:
        thread.join(timeout=45)
        assert not thread.is_alive(), f"worker hung ({len(failures)} failures)"

    assert not failures, failures
    every_id = [identifier for ids in collected.values() for identifier in ids]
    assert len(every_id) == threads * per_thread
    assert len(set(every_id)) == threads * per_thread, "an id was reused"
    for ids in collected.values():
        assert ids == sorted(ids), "each writer's ids strictly increase"
        assert all(left < right for left, right in zip(ids, ids[1:], strict=False))

    replayed = list(Event.objects.order_by("id").values_list("id", flat=True))
    assert len(replayed) == threads * per_thread, "every row is replayable"
    assert replayed == sorted(replayed)
