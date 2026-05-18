"""cantus.adapters — bridges to MCP and Anthropic Memory tool spec (v0.3.2).

The adapter layer is a pure conversion utility: it does NOT alter Skill or
Memory runtime behaviour and does NOT register a new protocol kind. The
package exposes exactly three top-level callables:

- ``export_as_mcp_server(skills, *, name, version)`` — wrap a list of cantus
  Skills as an MCP server (requires ``cantus[mcp]`` extras).
- ``import_mcp_server(*, transport, command_or_url)`` — connect to a remote
  MCP server and return a list of cantus Skills (requires ``cantus[mcp]``).
- ``expose_as_anthropic_memory_tool(memory)`` — return a JSON-serialisable
  dict matching the Anthropic Memory tool spec (no SDK dependency).

The two MCP entries lazy-import the ``mcp`` SDK only when called; the
Anthropic Memory adapter is pure Python and ships in the core install.
"""

from __future__ import annotations

from typing import Any


def export_as_mcp_server(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.mcp_server (Task 3.1)."""
    from cantus.adapters.mcp_server import export_as_mcp_server as _impl

    return _impl(*args, **kwargs)


def import_mcp_server(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.mcp_client (Task 4.1)."""
    from cantus.adapters.mcp_client import import_mcp_server as _impl

    return _impl(*args, **kwargs)


def expose_as_anthropic_memory_tool(*args: Any, **kwargs: Any) -> Any:
    """Stub. Implemented in cantus.adapters.anthropic_memory (Task 2.1)."""
    from cantus.adapters.anthropic_memory import (
        expose_as_anthropic_memory_tool as _impl,
    )

    return _impl(*args, **kwargs)


__all__ = [
    "export_as_mcp_server",
    "import_mcp_server",
    "expose_as_anthropic_memory_tool",
]
