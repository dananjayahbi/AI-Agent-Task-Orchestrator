"""Insert-only database guard for ``events_event`` (MT-1.9-04; Section 12.5).

The application role keeps INSERT (writers) and SELECT (replay,
viewer) but cannot UPDATE or DELETE audit rows: a row trigger enforces
it even when the role owns the table, and the REVOKEs close the ACL
layer. Statements are idempotent (running the one-shot migrate service
twice is safe) and PostgreSQL-only — see
``apps.events.migrations._guards`` for the full recorded reading.
"""

from django.db import migrations

from apps.events.migrations._guards import add_event_guard, remove_event_guard


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_event_guard, remove_event_guard),
    ]
