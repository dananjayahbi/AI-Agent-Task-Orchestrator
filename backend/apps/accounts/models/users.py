"""The user entity (parent plan Section 7.1; MT-1.2-01).

Django's ``AbstractUser`` supplies exactly the authentication material the
plan's owner model needs — username, the password *hash* (NFR-07: plaintext
passwords are never stored; Django's PBKDF2 hasher does this by default) and
``is_active`` — with no plan field invented or dropped (Section 20.5).
``AUTH_USER_MODEL`` points at this model from WP-1.1's settings (base.py)
before the first migration exists, so auth/contenttypes bind to it from the
start.

The entity is deliberately minimal: OQ-09 (owner authentication strength)
recorded "strong password plus optional TOTP, passkeys later" as a deferral to
M1 — no TOTP/second-factor fields are invented ahead of that decision (Section
20.1, rule 5: no hidden decisions).
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """The owner account backing login, token ownership and device binding."""

    class Meta(AbstractUser.Meta):
        """Keep the framework's default ordering/labels; no overrides."""
