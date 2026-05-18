"""MCP server adapter — wraps cantus Skills as MCP tool definitions.

`export_as_mcp_server(skills, *, name, version)` validates inputs and
returns an `McpServer` instance. `McpServer.tools` reflects each Skill's
`spec_for_llm()` output directly into MCP tool fields (`name`,
`description`, `inputSchema`) with no field rewrite. `McpServer.run()`
validates the transport, performs a fail-loud port-in-use probe for HTTP
transport, then delegates to the `mcp` SDK (which is imported lazily; if
not installed, callers see `ImportError` with an actionable
`pip install cantus[mcp]` hint).
"""

from __future__ import annotations

import re
import socket
from typing import Any, Literal

from cantus.protocols.skill import Skill

# Alphanumeric leader followed by alphanumeric, dot, underscore, or hyphen.
# Matches semantic-versioning and reverse-DNS-style names while blocking
# path separators, shell metacharacters, JSON delimiters, and whitespace.
_NAME_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_NAME_VERSION_MAX = 64


def _validate_name_or_version(value: Any, *, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field} must be alphanumeric [A-Za-z0-9][A-Za-z0-9._-]*, "
            f"length 1-{_NAME_VERSION_MAX}: got empty or non-string value"
        )
    if len(value) > _NAME_VERSION_MAX:
        raise ValueError(
            f"{field} must be alphanumeric: length {len(value)} exceeds "
            f"{_NAME_VERSION_MAX} characters"
        )
    if not _NAME_VERSION_RE.match(value):
        raise ValueError(
            f"{field} must be alphanumeric matching {_NAME_VERSION_RE.pattern}, "
            f"got {value!r}"
        )


class McpServer:
    """Thin holder for a list of MCP tool dicts derived from cantus Skills.

    The class is intentionally inert at construction time so that
    `export_as_mcp_server` can return an introspectable server object
    without requiring the `mcp` SDK. The SDK is only imported when
    `run()` is called.
    """

    def __init__(self, skills: list[Skill], *, name: str, version: str) -> None:
        self.name = name
        self.version = version
        self._skills: list[Skill] = list(skills)

    @property
    def tools(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for sk in self._skills:
            spec = sk.spec_for_llm()
            out.append(
                {
                    "name": spec["name"],
                    "description": spec["description"],
                    "inputSchema": spec["args_schema"],
                }
            )
        return out

    def run(
        self,
        *,
        transport: Literal["stdio", "http"],
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        if transport not in ("stdio", "http"):
            raise ValueError(
                f"transport must be 'stdio' or 'http', got {transport!r}"
            )

        if transport == "http":
            # Fail-loud port-in-use probe before delegating to the SDK.
            # The probe disables SO_REUSEADDR so a busy port surfaces
            # OSError("Address already in use") synchronously.
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            try:
                probe.bind((host, port))
            except OSError as exc:
                raise OSError(
                    f"Address already in use: {host}:{port} "
                    f"(probe failed: {exc})"
                ) from exc
            finally:
                probe.close()

        # Lazy SDK import. Raises ImportError("... pip install cantus[mcp]")
        # if the `mcp` SDK is not installed.
        from cantus.adapters.mcp import _start_server

        _start_server(
            name=self.name,
            version=self.version,
            tools=self.tools,
            skills=self._skills,
            transport=transport,
            host=host,
            port=port,
        )


def export_as_mcp_server(
    skills: list[Skill],
    *,
    name: str,
    version: str,
) -> McpServer:
    """Validate inputs and return an :class:`McpServer` wrapping the Skills."""
    _validate_name_or_version(name, field="name")
    _validate_name_or_version(version, field="version")

    if not isinstance(skills, list) or len(skills) == 0:
        raise ValueError(
            "export_as_mcp_server requires at least one Skill in the input list"
        )
    for sk in skills:
        if not isinstance(sk, Skill):
            raise TypeError(
                f"export_as_mcp_server expects list[Skill], "
                f"got element of type {type(sk).__name__}"
            )

    return McpServer(skills, name=name, version=version)


__all__ = ["McpServer", "export_as_mcp_server"]
