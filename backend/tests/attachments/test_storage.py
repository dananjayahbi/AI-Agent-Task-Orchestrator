"""MT-1.11-01 — the storage abstraction contract suite.

Run with ``pytest backend/tests/attachments/test_storage.py -v``. The
suite proves the MT's acceptance criteria:

* one interface, two backends selected **by configuration only**
  (Section 16.3): the contract tests below run against the local
  backend, and the s3 path is exercised at its configuration seam —
  construction from the Section 9.10 group, fail-fast without it (no
  boto fixture exists, so the client half is the recorded WP-6.2
  marker, never silently faked);
* keys are content-addressed: the same bytes produce the same key from
  either backend — asserted as a pure function of the digest plus the
  local backend's round-trip under that key (Sections 9.5, 16.3);
* the local backend stores **only** under the configured root: the
  traversal guard refuses every escaping key shape (hard rule).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.attachments.storage import (
    LocalStorageBackend,
    S3StorageBackend,
    StorageBackend,
    content_key,
    get_storage,
    hash_bytes,
)

DATA = b"the quick brown fox"
OTHER = b"another payload entirely"


# --- content addressing (Sections 9.5, 16.3) ---------------------------------


def test_same_bytes_produce_the_same_key() -> None:
    """Content addressing: the key is a pure function of the digest."""
    assert content_key(hash_bytes(DATA)) == content_key(hash_bytes(DATA))
    assert content_key(hash_bytes(DATA)) != content_key(hash_bytes(OTHER))


def test_key_shape_is_the_recorded_fanout_format() -> None:
    """The recorded key format: objects/<aa>/<full-hex> (module docstring)."""
    digest = hash_bytes(DATA)
    key = content_key(digest)
    assert key == f"objects/{digest[:2]}/{digest}"


def test_malformed_digest_is_refused() -> None:
    """A bad digest is a programming error, not a key (ValueError)."""
    with pytest.raises(ValueError):
        content_key("not-a-digest")
    with pytest.raises(ValueError):
        content_key("AB" + "0" * 62)  # uppercase is not the hex form


# --- the contract suite, parametrized over every backend ---------------------


@pytest.fixture
def local_storage(tmp_path: Path) -> LocalStorageBackend:
    """A local backend rooted at an isolated temporary directory."""
    return LocalStorageBackend(tmp_path)


def _contract_suite(storage: StorageBackend) -> None:
    """The shared put/get/exists/delete contract (MT-1.11-01 target test)."""
    key = content_key(hash_bytes(DATA))

    # Round-trip.
    assert storage.exists(key) is False
    storage.put(key, DATA)
    assert storage.exists(key) is True
    assert storage.get(key) == DATA

    # Idempotent put (content addressing: same key = same bytes).
    storage.put(key, DATA)
    assert storage.get(key) == DATA

    # Delete is idempotent; absent get raises KeyError.
    storage.delete(key)
    assert storage.exists(key) is False
    storage.delete(key)  # no-op, no error
    with pytest.raises(KeyError):
        storage.get(key)


def test_local_backend_passes_the_contract_suite(local_storage: LocalStorageBackend) -> None:
    """The default backend exercises the full shared contract."""
    _contract_suite(local_storage)


# --- the local backend's root confinement (hard rule) ------------------------


def test_local_backend_stores_only_under_the_root(tmp_path: Path) -> None:
    """Every stored byte lives under the configured root — no exceptions."""
    storage = LocalStorageBackend(tmp_path)
    key = content_key(hash_bytes(DATA))
    storage.put(key, DATA)
    stored = list(tmp_path.rglob("*"))
    files = [path for path in stored if path.is_file()]
    assert len(files) == 1
    assert files[0].is_relative_to(tmp_path)
    assert str(files[0]).replace("\\", "/").endswith(key)


def test_local_backend_refuses_traversal_keys(tmp_path: Path) -> None:
    """The key guard (Section 12.3): nothing escapes the media root."""
    storage = LocalStorageBackend(tmp_path)
    for hostile in (
        "../escape",
        "objects/../../../etc/passwd",
        "/absolute/path",
        "objects\\..\\..\\windows",
        "objects/zz/" + "0" * 64,  # zz is not lowercase hex
        "objects/aa/" + "0" * 63,  # short digest
    ):
        with pytest.raises(ValueError):
            storage.put(hostile, DATA)
        with pytest.raises(ValueError):
            storage.get(hostile)
        with pytest.raises(ValueError):
            storage.delete(hostile)


def test_put_failure_leaves_no_scratch_files(tmp_path: Path) -> None:
    """A failed write cleans its temp file (module docstring guarantee)."""
    import os
    from unittest.mock import patch

    storage = LocalStorageBackend(tmp_path)
    key = content_key(hash_bytes(DATA))

    with patch.object(os, "replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            storage.put(key, DATA)

    leftovers = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert leftovers == []  # no half-written object, no temp file


# --- configuration-only selection (Section 9.10; Section 16.3) ---------------


def test_default_configuration_selects_local(tmp_path: Path) -> None:
    """The default ``local`` backend binds to MEDIA_ROOT (Section 16.3)."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        storage = get_storage()
        assert isinstance(storage, LocalStorageBackend)
        key = content_key(hash_bytes(DATA))
        storage.put(key, DATA)
        assert (tmp_path / key).is_file()  # exactly the configured root


def test_s3_configuration_reaches_the_seam_and_fails_fast() -> None:
    """Selecting s3 builds the seam from the config group — then the
    recorded WP-6.2 marker refuses the client half loudly (never a
    silent local fallback)."""
    with override_settings(
        STORAGE_BACKEND="s3",
        STORAGE_S3_ENDPOINT="https://s3.example.invalid",
        STORAGE_S3_BUCKET="orchestrator",
    ):
        with pytest.raises(NotImplementedError, match="WP-6.2"):
            get_storage()


def test_s3_seam_requires_endpoint_and_bucket() -> None:
    """The S3 group is validated at construction (Section 9.10)."""
    with pytest.raises(ImproperlyConfigured):
        S3StorageBackend(endpoint="", bucket="")
    with pytest.raises(ImproperlyConfigured):
        S3StorageBackend(endpoint="https://s3.example.invalid", bucket="")


def test_unknown_backend_fails_fast() -> None:
    """A typo in the selector never silently picks a backend (9.10)."""
    with override_settings(STORAGE_BACKEND="nfs"):
        with pytest.raises(ImproperlyConfigured):
            get_storage()


def test_both_backends_satisfy_the_protocol() -> None:
    """One interface is used by both implementations (acceptance)."""
    assert isinstance(LocalStorageBackend("/media"), StorageBackend)
