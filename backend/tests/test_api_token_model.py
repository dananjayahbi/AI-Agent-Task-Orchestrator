"""MT-1.2-02 — API Token model invariants (Sections 7.2, 7.3, 7.4; ADR-004).

Proves the Section 7.2 field set and the security invariants that make token
theft mitigations (Section 12.1) real:

* the three kinds are the closed enum; every canonical field exists;
* ``kind = agent`` requires a well-formed ``project_id`` — at the model
  (``full_clean``), at the database (check constraints), so a project-less or
  malformed agent token cannot be represented (ADR-004, FR-SEC-01);
* only ``hash`` is stored — plaintext never appears in any field, ``str()`` or
  API response (Section 7.2, FR-SEC-04);
* the canonical validity predicate (``is_valid`` + ``matches_project`` +
  ``is_usable_for``) is tested for all three kinds across revoked, expired
  and cross-project states (FR-SEC-02; Section 12.1 "expiring").

Run with ``pytest backend/tests -k token`` (MT test command).
"""

from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken, TokenKind, User
from apps.accounts.services.tokens import generate_token, hash_token

PID_ONE = "PID00001"
PID_TWO = "PID00002"

OWNER_PASSWORD = "model-test-password-1!"  # pragma: allowlist secret


@pytest.fixture
def owner(db: None) -> User:
    """The account every token row belongs to (Section 7.1)."""
    return User.objects.create_user(username="owner", password=OWNER_PASSWORD)


def _token(owner: User, **kwargs: object) -> ApiToken:
    """Build an unsaved token row with sensible defaults for each test."""
    values: dict[str, object] = {
        "kind": TokenKind.OWNER_SESSION,
        "hash": hash_token(generate_token()),
        "user": owner,
    }
    values.update(kwargs)
    return ApiToken(**values)


# --- Section 7.2 / ADR-004: agent kind requires project_id -----------------


def test_agent_token_without_project_is_rejected_by_the_database(owner: User) -> None:
    """The check constraint makes a project-less agent row impossible (7.4)."""
    token = _token(owner, kind=TokenKind.AGENT)
    with pytest.raises(IntegrityError), transaction.atomic():
        token.save()


def test_agent_token_without_project_is_rejected_by_the_model(owner: User) -> None:
    """``full_clean`` mirrors the DB rule so API layers get a field error."""
    token = _token(owner, kind=TokenKind.AGENT)
    with pytest.raises(ValidationError) as excinfo:
        token.full_clean()
    assert "project_id" in excinfo.value.error_dict


def test_agent_token_with_project_passes_validation(owner: User) -> None:
    """ADR-004 happy path: agent token bound to exactly one canonical PID."""
    token = _token(owner, kind=TokenKind.AGENT, project_id=PID_ONE, scopes=["coder"])
    token.full_clean()
    token.save()
    assert ApiToken.objects.get(pk=token.pk).project_id == PID_ONE


def test_malformed_project_id_is_rejected(owner: User) -> None:
    """Section 7.3: PID + five digits, enforced in model *and* database."""
    bad_model = _token(owner, kind=TokenKind.AGENT, project_id="project-1")
    with pytest.raises(ValidationError) as excinfo:
        bad_model.full_clean()
    assert "project_id" in excinfo.value.error_dict

    # Bypassing full_clean still cannot persist a malformed value.
    bypass = _token(owner, kind=TokenKind.AGENT, project_id="PID000001")
    with pytest.raises(IntegrityError), transaction.atomic():
        bypass.save()


def test_non_agent_kinds_may_omit_project_id(owner: User) -> None:
    """Only ``agent`` is project-bound (Section 7.2: required for agent)."""
    for kind in (TokenKind.OWNER_SESSION, TokenKind.DEVICE):
        token = _token(owner, kind=kind)
        token.full_clean()
        token.save()
    assert (
        ApiToken.objects.filter(project_id__isnull=True).exclude(kind=TokenKind.AGENT).count() == 2
    )


# --- The canonical validity predicate (all three kinds) --------------------


@pytest.mark.parametrize("kind", list(TokenKind))
def test_live_token_is_valid_and_scoped_correctly(owner: User, kind: str) -> None:
    """Not revoked + no expiry: valid; only the agent kind is project-bound."""
    token = _token(
        owner,
        kind=kind,
        project_id=PID_ONE if kind == TokenKind.AGENT else None,
    )
    token.full_clean()
    assert token.is_valid() is True
    if kind == TokenKind.AGENT:
        assert token.matches_project(PID_ONE) is True
        assert token.matches_project(PID_TWO) is False
        assert token.is_usable_for(PID_ONE) is True
        assert token.is_usable_for(PID_TWO) is False
    else:
        # Owner sessions and devices address any project (7.2 binds only agent).
        assert token.matches_project(PID_TWO) is True
        assert token.is_usable_for(PID_TWO) is True


@pytest.mark.parametrize("kind", list(TokenKind))
def test_revoked_token_fails_the_predicate_for_every_kind(owner: User, kind: str) -> None:
    """FR-SEC-02: revocation invalidates regardless of scope or expiry."""
    token = _token(
        owner,
        kind=kind,
        project_id=PID_ONE if kind == TokenKind.AGENT else None,
        revoked_at=timezone.now(),
    )
    assert token.is_valid() is False
    assert token.is_usable_for(PID_ONE) is False


@pytest.mark.parametrize("kind", list(TokenKind))
def test_expired_token_fails_the_predicate_for_every_kind(owner: User, kind: str) -> None:
    """Section 12.1 "expiring": a past ``expires_at`` is dead even in-scope."""
    token = _token(
        owner,
        kind=kind,
        project_id=PID_ONE if kind == TokenKind.AGENT else None,
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert token.is_valid() is False
    assert token.is_usable_for(PID_ONE) is False


def test_future_and_null_expiry_are_live(owner: User) -> None:
    """``expires_at`` null means no expiry; a future instant stays usable."""
    no_expiry = _token(owner, expires_at=None)
    assert no_expiry.is_valid() is True
    future = _token(owner, expires_at=timezone.now() + timedelta(hours=1))
    assert future.is_valid() is True


def test_usable_for_combines_both_halves(owner: User) -> None:
    """The single source ANDs liveness with project scope (ADR-004)."""
    agent = _token(owner, kind=TokenKind.AGENT, project_id=PID_ONE)
    assert agent.is_usable_for(PID_ONE) is True
    assert agent.is_usable_for(PID_TWO) is False  # wrong project, even if live

    agent.revoked_at = timezone.now()
    assert agent.is_usable_for(PID_ONE) is False  # right project, revoked


# --- Hashed storage only (Section 7.2; FR-SEC-04) --------------------------


def test_plaintext_token_is_never_persisted(owner: User) -> None:
    """Only the SHA-256 hash is stored — nowhere does plaintext survive."""
    plaintext = generate_token()
    token = _token(owner, hash=hash_token(plaintext))
    token.save()

    assert token.hash == hashlib.sha256(plaintext.encode()).hexdigest()
    stored_values = [str(field.value_from_object(token)) for field in ApiToken._meta.fields]
    assert plaintext not in stored_values

    # Refetch through the ORM: the database copy carries no plaintext either.
    refetched = ApiToken.objects.get(pk=token.pk)
    assert plaintext not in repr(refetched.__dict__)
    # Identification never formats the secret (log-line safety).
    assert plaintext not in str(refetched)
    assert refetched.hash not in str(refetched)


def test_hash_never_appears_in_api_representations(owner: User) -> None:
    """Risk note: any response leaking ``hash`` would leak every token."""
    api = APIClient()
    login = api.post(
        "/api/v1/auth/login",
        {"username": owner.username, "password": OWNER_PASSWORD},
    )
    assert login.status_code == 200
    stored_hashes = [row.hash for row in ApiToken.objects.all()]
    assert stored_hashes, "login must have recorded an owner_session row"

    refresh = api.post("/api/v1/auth/refresh")
    logout = api.post("/api/v1/auth/logout")
    for response in (login, refresh, logout):
        body = response.content.decode()
        for stored_hash in stored_hashes:
            assert stored_hash not in body, "token hash leaked through the API"


def test_scopes_round_trip_as_role_list(owner: User) -> None:
    """Section 12.2 roles ride on scopes (MT-1.2-05 reading); default empty."""
    fresh = _token(owner, kind=TokenKind.AGENT, project_id=PID_ONE)
    assert fresh.scopes == []  # default list, never null

    fresh.scopes = ["coder", "auditor"]
    fresh.save()
    refetched = ApiToken.objects.get(pk=fresh.pk)
    assert refetched.scopes == ["coder", "auditor"]
    refetched.full_clean()  # still canonical after round-trip
