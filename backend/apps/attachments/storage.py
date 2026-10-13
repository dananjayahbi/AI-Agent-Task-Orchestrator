"""Content-addressed storage abstraction (MT-1.11-01; Sections 9.5, 16.3, 9.10).

One interface, two implementations, selected **by configuration only**
(Section 16.3): the local named-volume backend (default) and an
S3-compatible seam reserved for WP-6.2. Patch artifacts (M3) share this
abstraction, so the operations are deliberately generic — opaque bytes
in, an opaque content-addressed key out; nothing attachment-specific
lives here (MT-1.11-01 risk note).

**Content addressing** (Sections 9.5, 16.3): the key is derived from the
sha256 of the bytes — identical bytes produce the identical key from
either backend, which is the foundation MT-1.11-02's de-duplication
builds on. The plan fixes "content-hash keys" but no key *format*; the
one recorded choice (WP changelog, Section 20.1 item 5) is
``objects/<aa>/<full-sha256-hex>`` — a two-level fan-out so the local
volume never holds a single flat directory of millions of entries. The
format is an implementation detail behind :func:`content_key`; callers
never parse it (pagination.md-style opacity, one level up).

**Security** (Section 12.3): the local backend treats keys as untrusted
and refuses anything that could escape the media root (traversal,
absolute paths, separators) — uploads are *never* stored outside the
configured root (hard rule; MT-1.11-01 acceptance). The root itself comes
from the Section 9.10 storage group (``MEDIA_ROOT``, default ``/media``).

**Configuration** (Section 9.10; configuration.md storage-backend rows):
``STORAGE_BACKEND`` ∈ {``local``, ``s3``}; the S3 endpoint/bucket/
credential pair is read here so the whole group resolves from one module.
Selecting ``s3`` before WP-6.2 wires the client raises at construction —
fail fast (Section 9.10 startup validation) rather than silently serving
local bytes under an s3 label. No secrets or environment-specific paths
are committed (Section 20.4 item 3).
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Key format (recorded choice, module docstring): lowercase hex sha256
# behind a two-level fan-out. The strict matcher doubles as the local
# backend's traversal guard — nothing else can name a file.
_KEY_PATTERN: Final = re.compile(r"\Aobjects/[0-9a-f]{2}/[0-9a-f]{64}\Z")
_SHA256_PATTERN: Final = re.compile(r"\A[0-9a-f]{64}\Z")


def content_key(sha256_hex: str) -> str:
    """The content-addressed storage key for one sha256 digest.

    Pure function of the digest — the same bytes yield the same key from
    any backend (Section 16.3). A malformed digest is a programming
    error (digests come from :func:`hash_bytes`, never from clients).
    """
    if not _SHA256_PATTERN.match(sha256_hex):
        raise ValueError(f"sha256 digest must be 64 lowercase hex chars, got {sha256_hex!r}")
    return f"objects/{sha256_hex[:2]}/{sha256_hex}"


def hash_bytes(data: bytes) -> str:
    """Hex sha256 of *data* — the de-duplication identity (Section 9.5)."""
    return hashlib.sha256(data).hexdigest()


@runtime_checkable
class StorageBackend(Protocol):
    """The seam every consumer uses (attachments now, patch artifacts in M3)."""

    def put(self, key: str, data: bytes) -> None:
        """Store *data* under the content-addressed *key*.

        Idempotent: writing an existing key is a no-op (content addressing
        means the bytes are already there — MT-1.11-02 de-duplication).
        """
        ...

    def get(self, key: str) -> bytes:
        """Return the stored bytes for *key*; raise KeyError when absent."""
        ...

    def exists(self, key: str) -> bool:
        """Whether *key* is stored."""
        ...

    def delete(self, key: str) -> None:
        """Remove the object at *key*; absent keys are a no-op (idempotent)."""
        ...


class LocalStorageBackend:
    """Named-volume backend (Section 16.3 default) rooted at ``MEDIA_ROOT``.

    Writes are atomic: a temporary file inside the *same* directory, then
    ``os.replace`` — a crashed upload never leaves a half-written object
    under a content key. The temporary file lives under the media root too
    (hard rule: nothing outside it).
    """

    def __init__(self, root: str | Path) -> None:
        """Bind to an absolute media root (creating it on demand)."""
        self._root = Path(root)

    def _path_for(self, key: str) -> Path:
        """Resolve *key* inside the root, refusing anything that escapes."""
        # _KEY_PATTERN is the traversal guard (module docstring): only the
        # exact content-key shape passes, so the join cannot leave the root.
        if not _KEY_PATTERN.match(key):
            raise ValueError(f"invalid storage key {key!r}")
        return self._root / key

    def put(self, key: str, data: bytes) -> None:
        """Atomically store *data* under *key*; existing keys are a no-op."""
        path = self._path_for(key)
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        # Temp file in the destination directory so os.replace is atomic
        # on every filesystem (same-volume requirement of os.replace).
        descriptor, temp_name = tempfile.mkstemp(dir=path.parent, prefix=".put-")
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
            os.replace(temp_name, path)
        except BaseException:
            # Never leave scratch bytes behind, on any failure path.
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def get(self, key: str) -> bytes:
        """Read the stored bytes; absent key answers KeyError."""
        path = self._path_for(key)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise KeyError(key) from exc

    def exists(self, key: str) -> bool:
        """Whether the object exists (regular file only)."""
        return self._path_for(key).is_file()

    def delete(self, key: str) -> None:
        """Remove the object; absent keys are a no-op (idempotent)."""
        self._path_for(key).unlink(missing_ok=True)


class S3StorageBackend:
    """S3-compatible seam (Section 16.3) — reserved, client lands WP-6.2.

    The configuration half exists now so the backend is *reachable by
    configuration only* (MT-1.11-01 acceptance): construction validates
    the Section 9.10 group and fails fast when the group is incomplete.
    The client wiring (endpoint/bucket/credentials → object operations)
    is WP-6.2's; until then selecting ``s3`` raises at startup, which is
    the honest failure — never a silent local fallback.
    """

    def __init__(self, *, endpoint: str, bucket: str) -> None:
        """Fail fast: the s3 client itself arrives with WP-6.2."""
        # Both are validated non-empty by prod.py startup checks; keep the
        # constructor honest for dev/test paths that reach it directly.
        if not endpoint or not bucket:
            raise ImproperlyConfigured(
                "ORCHESTRATOR_STORAGE_S3_ENDPOINT and _BUCKET are required "
                "when ORCHESTRATOR_STORAGE_BACKEND=s3 (Section 9.10)."
            )
        raise NotImplementedError(
            "The S3-compatible client lands with WP-6.2 (Section 16.3); "
            "the s3 backend is a configuration-only seam until then."
        )

    def put(self, key: str, data: bytes) -> None:  # pragma: no cover - unreachable
        """WP-6.2 replaces this stub with the real PutObject call."""
        raise NotImplementedError

    def get(self, key: str) -> bytes:  # pragma: no cover - unreachable
        """WP-6.2 replaces this stub with the real GetObject call."""
        raise NotImplementedError

    def exists(self, key: str) -> bool:  # pragma: no cover - unreachable
        """WP-6.2 replaces this stub with the real HeadObject call."""
        raise NotImplementedError

    def delete(self, key: str) -> None:  # pragma: no cover - unreachable
        """WP-6.2 replaces this stub with the real DeleteObject call."""
        raise NotImplementedError


def get_storage() -> StorageBackend:
    """The configured backend instance (Section 9.10 selector).

    ``local`` (default) binds to ``settings.MEDIA_ROOT``; ``s3`` builds
    the reserved seam from the S3 group. An unknown selector fails fast —
    a typo in ``ORCHESTRATOR_STORAGE_BACKEND`` must not silently pick a
    backend (Section 9.10 startup validation).
    """
    backend = settings.STORAGE_BACKEND
    if backend == "local":
        return LocalStorageBackend(settings.MEDIA_ROOT)
    if backend == "s3":
        return S3StorageBackend(
            endpoint=settings.STORAGE_S3_ENDPOINT,
            bucket=settings.STORAGE_S3_BUCKET,
        )
    raise ImproperlyConfigured(
        f"Unknown ORCHESTRATOR_STORAGE_BACKEND {backend!r} — expected 'local' or 's3'."
    )


__all__ = [
    "LocalStorageBackend",
    "S3StorageBackend",
    "StorageBackend",
    "content_key",
    "get_storage",
    "hash_bytes",
]
