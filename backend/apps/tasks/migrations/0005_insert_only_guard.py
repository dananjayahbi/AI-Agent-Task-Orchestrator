"""Insert-only database guard for ``tasks_tasktransition`` (MT-1.9-04).

Section 12.5/7.4 rule 5: the application role cannot update or delete
audit rows — WP-1.5's model-level immutability (``0003_tasktransition``)
now gets its database-level half for the Task Transition history, the
first append-only table. The statements live with WP-1.9's shared
guard (``apps.events.migrations._guards``); idempotent and
PostgreSQL-only, as documented there.
"""

from django.db import migrations

from apps.events.migrations._guards import add_transition_guard, remove_transition_guard


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0004_task_lease_generation"),
    ]

    operations = [
        migrations.RunPython(add_transition_guard, remove_transition_guard),
    ]
