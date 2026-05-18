"""MCP client adapter — connect to a remote MCP server, return cantus Skills.

`import_mcp_server(*, transport, command_or_url)` validates the
``command_or_url`` against a strict policy (shell-metacharacter rejection
for stdio, HTTP(S)-only for http), then lazy-imports the ``mcp`` SDK
gate to enumerate remote tools and build a cantus :class:`Skill` per
remote tool.

Each returned Skill bypasses the standard signature-introspection path
so its ``spec_for_llm()`` returns the remote tool's MCP ``inputSchema``
verbatim (no Pydantic schema rewrite). The Skill carries a read-only
``is_remote = True`` attribute for log / Inspector display, but the
attribute does NOT leak into ``spec_for_llm()`` (the v0.3.0 shape
contract holds: top-level keys remain ``{"name", "description",
"args_schema"}``).

Failure surfaces follow the v0.3.2 error naming convention:
handshake-time failures raise ``RuntimeError("mcp_handshake_failed: ...")``
and call-time failures raise ``RuntimeError("mcp_remote_error: ...")``
which the cantus agent loop wraps as ``ToolErrorObservation``.
"""

from __future__ import annotations

import urllib.parse
from typing import Any, Literal

from cantus.protocols.skill import Skill

_SHELL_METACHARS: tuple[str, ...] = ("|", ">", "<", "&", ";", "$", "`", "\n", "\r")


def _validate_stdio_command(command_or_url: str) -> None:
    if not isinstance(command_or_url, str) or not command_or_url:
        raise ValueError(
            "command must be a binary path, not shell syntax: "
            "empty or non-string command"
        )
    if any(ch in command_or_url for ch in _SHELL_METACHARS):
        raise ValueError(
            "command must be a binary path, not shell syntax: "
            f"shell metacharacters detected in {command_or_url!r}"
        )


def _validate_http_url(command_or_url: str) -> None:
    if not isinstance(command_or_url, str):
        raise ValueError(
            f"command_or_url must be http(s) URL, got {type(command_or_url).__name__}"
        )
    parsed = urllib.parse.urlparse(command_or_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            f"command_or_url must be http(s) URL with non-empty host, "
            f"got {command_or_url!r}"
        )


def _connect_and_list_mcp_tools(transport: str, command_or_url: str) -> list[dict[str, Any]]:
    """Lazy SDK call returning ``[{"name", "description", "inputSchema"}, ...]``.

    Tests monkeypatch this symbol; production calls the actual mcp SDK
    via the ``cantus.adapters.mcp`` gate, which raises ImportError when
    the SDK is missing.
    """
    from cantus.adapters.mcp import _mcp_list_tools  # SDK gate

    return _mcp_list_tools(transport=transport, command_or_url=command_or_url)


def _call_remote_tool(
    transport: str,
    command_or_url: str,
    tool_name: str,
    args: dict[str, Any],
) -> Any:
    """Lazy SDK call dispatching a single remote `tools/call`.

    Tests monkeypatch this symbol.
    """
    from cantus.adapters.mcp import _mcp_call_tool  # SDK gate

    return _mcp_call_tool(
        transport=transport,
        command_or_url=command_or_url,
        tool_name=tool_name,
        args=args,
    )


class _RemoteSkill(Skill):
    """cantus Skill wrapper for an MCP tool exposed by a remote server."""

    is_remote = True

    def __init__(
        self,
        *,
        tool_name: str,
        description: str,
        input_schema: dict[str, Any],
        transport: str,
        command_or_url: str,
    ) -> None:
        # Intentionally bypass Skill.__init__: we do NOT want signature
        # introspection because the remote tool's schema is authoritative.
        self.name = tool_name
        self.description = description
        self._input_schema = input_schema
        self._transport = transport
        self._command_or_url = command_or_url
        self._pre_hook = None
        self._post_hook = None

    def spec_for_llm(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": self._input_schema,
        }

    def validate_args(self, args: dict[str, Any]) -> dict[str, Any]:
        # The remote server is authoritative for argument validation;
        # cantus only enforces that args is a dict at the protocol layer.
        if not isinstance(args, dict):
            raise TypeError(
                f"remote MCP tool args must be a dict, got {type(args).__name__}"
            )
        return dict(args)

    def run(self, **kwargs: Any) -> Any:
        try:
            return _call_remote_tool(
                self._transport,
                self._command_or_url,
                self.name,
                kwargs,
            )
        except Exception as exc:
            raise RuntimeError(
                f"mcp_remote_error: tool {self.name!r} on {self._command_or_url!r} "
                f"failed: {type(exc).__name__}: {exc}"
            ) from exc


def import_mcp_server(
    *,
    transport: Literal["stdio", "http"],
    command_or_url: str,
) -> list[Skill]:
    """Connect to a remote MCP server and return its tools as cantus Skills."""
    if transport == "stdio":
        _validate_stdio_command(command_or_url)
    elif transport == "http":
        _validate_http_url(command_or_url)
    else:
        raise ValueError(
            f"transport must be 'stdio' or 'http', got {transport!r}"
        )

    try:
        tools = _connect_and_list_mcp_tools(transport, command_or_url)
    except (RuntimeError, ValueError, OSError, ConnectionError) as exc:
        raise RuntimeError(
            f"mcp_handshake_failed: connection to {command_or_url!r} "
            f"failed during tools/list: {type(exc).__name__}: {exc}"
        ) from exc

    out: list[Skill] = []
    for t in tools:
        out.append(
            _RemoteSkill(
                tool_name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
                transport=transport,
                command_or_url=command_or_url,
            )
        )
    return out


__all__ = ["import_mcp_server"]
