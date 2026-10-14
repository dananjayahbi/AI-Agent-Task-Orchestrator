"""The four MCP prompts of parent plan Section 10.7 (FR-MCP-04; WP-2.8).

One module per prompt (MT-2.8-01…04) — ``start_work``, ``checkpoint``,
``submit_for_audit``, ``audit`` — assembled here into the registry
``server.create_server`` registers on the MCP server alongside the Section
10.5 tool catalog. Two invariants pin this package (tests/test_prompts.py):

* **Descriptions over one tool surface** (ADR-011, NFR-08): every prompt
  names only tools and error codes that already exist in Sections 10.5 /
  9.2, and each text states that the same workflow is available from the
  tool descriptions and rules block alone — a client that never surfaces
  prompts loses guidance, never capability.
* **No invented arguments** (MT-2.8-01 risk note): the plan defines no
  prompt arguments, so every prompt renders a fixed text.

Registration is the same seam pattern as tools: ``build_prompts`` produces
the SDK :class:`~mcp.server.mcpserver.prompts.Prompt` objects (a callable
returning the text), and ``create_server`` adds them only when a bound
session runtime exists — an unbound skeleton server stays empty, exactly as
the WP-2.1 contract requires.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from mcp.server.mcpserver.prompts import Prompt

from . import audit, checkpoint, start_work, submit_for_audit

__all__ = ["PROMPT_NAMES", "PROMPT_SPECS", "PromptSpec", "build_prompts"]


@dataclass(frozen=True, slots=True)
class PromptSpec:
    """One registered prompt: stable name, client-facing description, text."""

    name: str
    description: str
    text: str


#: The Section 10.7 prompts, in the plan's catalog order.
PROMPT_SPECS: Final[tuple[PromptSpec, ...]] = (
    PromptSpec(start_work.NAME, start_work.DESCRIPTION, start_work.TEXT),
    PromptSpec(checkpoint.NAME, checkpoint.DESCRIPTION, checkpoint.TEXT),
    PromptSpec(submit_for_audit.NAME, submit_for_audit.DESCRIPTION, submit_for_audit.TEXT),
    PromptSpec(audit.NAME, audit.DESCRIPTION, audit.TEXT),
)

#: The exact prompt set ``prompts/list`` must advertise (WP-2.8 acceptance).
PROMPT_NAMES: Final[tuple[str, ...]] = tuple(spec.name for spec in PROMPT_SPECS)


def _renderer(text: str) -> Callable[[], str]:
    """One zero-argument renderer — the plan defines no prompt arguments."""

    def render() -> str:
        return text

    return render


def build_prompts() -> list[Prompt]:
    """Instantiate every registered prompt for the MCP server.

    The SDK's ``Prompt`` takes the zero-argument ``fn`` whose return value
    becomes the rendered user message; names and descriptions travel on
    ``prompts/list`` verbatim from the specs.
    """
    return [
        Prompt(
            name=spec.name,
            title=None,
            description=spec.description,
            arguments=None,  # the plan defines no prompt arguments (MT-2.8-01)
            fn=_renderer(spec.text),
            icons=None,
            context_kwarg=None,  # no context parameter — the plan defines none
        )
        for spec in PROMPT_SPECS
    ]
