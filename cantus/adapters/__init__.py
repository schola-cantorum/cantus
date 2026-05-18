"""cantus.adapters — bridges to MCP, Anthropic Memory, and four
cross-framework targets (LangChain / DSPy / HuggingFace / OpenHands).

The adapter layer is a pure conversion utility: it does NOT alter Skill
or Memory runtime behaviour and does NOT register a new protocol kind.
The package exposes ten top-level callables (3 from v0.3.2 + 6 from
v0.3.3 + 1 from v0.3.4):

v0.3.2 (MCP + Anthropic Memory):
- ``export_as_mcp_server(skills, *, name, version)`` — wrap a list of
  cantus Skills as an MCP server (requires ``cantus[mcp]``).
- ``import_mcp_server(*, transport, command_or_url)`` — connect to a
  remote MCP server and return a list of cantus Skills.
- ``expose_as_anthropic_memory_tool(memory)`` — JSON-serialisable dict
  matching the Anthropic Memory tool spec (no SDK dependency).

v0.3.3 (cross-framework batch2):
- ``expose_as_langchain_tool(skill)`` / ``import_langchain_tool(tool)`` —
  cantus Skill <-> ``langchain_core.tools.BaseTool``
  (requires ``cantus[langchain]``).
- ``expose_as_dspy_tool(skill)`` / ``import_dspy_tool(tool)`` —
  cantus Skill <-> ``dspy.Tool``
  (requires ``cantus[dspy]``).
- ``expose_as_hf_tool(skill)`` — cantus Skill -> ``transformers.Tool``
  (requires ``cantus[huggingface]``).
- ``expose_as_openhands_action(skill)`` — cantus Skill ->
  ``openhands.events.Action`` (requires ``cantus[openhands]``;
  export-only — the import direction is permanently not applicable
  because ``Action`` is a declarative event record dispatched by the
  OpenHands host runtime, with no ``__call__`` for ``Skill.run`` to
  delegate to).

v0.3.4 (cross-framework batch3a — HF bidirectional close-out):
- ``import_hf_tool(tool)`` — cantus Skill <- ``transformers.Tool``
  (requires ``cantus[huggingface]``). Completes the HuggingFace
  bidirectional matrix; the OpenHands import direction is intentionally
  omitted, see ``expose_as_openhands_action`` above.

Every batch2/batch3 entry lazy-imports its SDK only when called; the core
``pip install cantus`` install still resolves ``import cantus.adapters``
without pulling any framework SDK.
"""

from __future__ import annotations

from typing import Any


def export_as_mcp_server(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.mcp_server."""
    from cantus.adapters.mcp_server import export_as_mcp_server as _impl

    return _impl(*args, **kwargs)


def import_mcp_server(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.mcp_client."""
    from cantus.adapters.mcp_client import import_mcp_server as _impl

    return _impl(*args, **kwargs)


def expose_as_anthropic_memory_tool(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.anthropic_memory."""
    from cantus.adapters.anthropic_memory import (
        expose_as_anthropic_memory_tool as _impl,
    )

    return _impl(*args, **kwargs)


def expose_as_langchain_tool(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.langchain (requires cantus[langchain])."""
    from cantus.adapters.langchain import expose_as_langchain_tool as _impl

    return _impl(*args, **kwargs)


def import_langchain_tool(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.langchain (requires cantus[langchain])."""
    from cantus.adapters.langchain import import_langchain_tool as _impl

    return _impl(*args, **kwargs)


def expose_as_dspy_tool(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.dspy (requires cantus[dspy])."""
    from cantus.adapters.dspy import expose_as_dspy_tool as _impl

    return _impl(*args, **kwargs)


def import_dspy_tool(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.dspy (requires cantus[dspy])."""
    from cantus.adapters.dspy import import_dspy_tool as _impl

    return _impl(*args, **kwargs)


def expose_as_hf_tool(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.huggingface (requires cantus[huggingface])."""
    from cantus.adapters.huggingface import expose_as_hf_tool as _impl

    return _impl(*args, **kwargs)


def import_hf_tool(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.huggingface (requires cantus[huggingface])."""
    from cantus.adapters.huggingface import import_hf_tool as _impl

    return _impl(*args, **kwargs)


def expose_as_openhands_action(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.openhands (requires cantus[openhands])."""
    from cantus.adapters.openhands import expose_as_openhands_action as _impl

    return _impl(*args, **kwargs)


__all__ = [
    # v0.3.2 — MCP + Anthropic Memory
    "export_as_mcp_server",
    "import_mcp_server",
    "expose_as_anthropic_memory_tool",
    # v0.3.3 — cross-framework batch2
    "expose_as_langchain_tool",
    "import_langchain_tool",
    "expose_as_dspy_tool",
    "import_dspy_tool",
    "expose_as_hf_tool",
    "expose_as_openhands_action",
    # v0.3.4 — cross-framework batch3a (HF bidirectional close-out)
    "import_hf_tool",
]
