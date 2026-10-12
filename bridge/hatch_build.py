"""Custom hatch build hook: ship the published manifest schema with the artifacts.

MT-2.2-02 (parent plan Section 10.3 step 2): structural validation runs against
the *published* ``schemas/manifest.v1.json`` — one canonical file in the repo
root, shared with the backend's manifest renderer (MT-1.3-05). A source checkout
reads that file directly; an installed package must read a copy the build places
inside the wheel at ``orchestrator_bridge/schemas/manifest.v1.json``.

Why a hook instead of static ``force-include`` TOML: the source path differs per
build context and TOML cannot express alternatives —

* repo checkout (``uv sync``/``uv run``, ``pip install .``, sdist build): the
  schema sits one level *above* the project root at ``../schemas/manifest.v1.json``;
* wheel built from the extracted sdist (what ``uv build`` does): the project
  root is the extracted ``orchestrator_bridge-<version>/`` directory, where the
  schema arrives as ``schemas/manifest.v1.json`` via this hook's sdist pass
  (hatchling force-includes this file into the sdist automatically).

The hook resolves the first candidate that exists and fails the build loudly
when neither does, so an artifact can never ship without its schema
(Section 20.4 item 4 — one schema, both consumers, no silent drift).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import (  # type: ignore[import-not-found] # hatchling: build-system-only, absent from the dev env
    BuildHookInterface,
)

#: Schema path relative to a root that already contains it (repo root or sdist root).
SCHEMA_RELPATH = Path("schemas") / "manifest.v1.json"
#: Where the schema lands inside the sdist, so a wheel built from it can find it.
SDIST_TARGET = "schemas/manifest.v1.json"
#: Where the schema lands inside the wheel (``manifest_validation._PACKAGED_SCHEMA``).
WHEEL_TARGET = "orchestrator_bridge/schemas/manifest.v1.json"


class ManifestSchemaBuildHook(BuildHookInterface):  # type: ignore[misc] # base is untyped here; hook API checked at build time
    """Force-include the canonical manifest schema into the sdist and the wheel."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        source = self._resolve_schema_source()
        target = SDIST_TARGET if self.target_name == "sdist" else WHEEL_TARGET
        build_data["force_include"][str(source)] = target

    def _resolve_schema_source(self) -> Path:
        """First existing candidate: project-root copy (sdist), then the checkout parent.

        Preferring ``<root>/schemas/`` keeps builds inside the project root
        whenever the artifact already carries the file; the parent lookup covers
        a source checkout, where the canonical file lives above ``bridge/``.
        """
        root = Path(self.root)
        candidates = (root / SCHEMA_RELPATH, root / ".." / SCHEMA_RELPATH)
        for candidate in candidates:
            source = candidate.resolve()
            if source.is_file():
                return source
        searched = ", ".join(str(candidate) for candidate in candidates)
        message = f"published manifest schema not found (searched: {searched})"
        raise FileNotFoundError(message)
