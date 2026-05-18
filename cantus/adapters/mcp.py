"""cantus.adapters.mcp — SDK gate module.

Importing this module triggers the `mcp` SDK import. When the SDK is not
installed (the user has not run `pip install cantus[mcp]`), the import
fails with an actionable :class:`ImportError`. This keeps the
`cantus.adapters.mcp_server` and `cantus.adapters.mcp_client` modules
importable without the SDK (so input validation and structural tests
work in core-only environments), while the *actual* `run()` and
`tools/list` SDK calls fail loud the moment they're invoked.
"""

from __future__ import annotations

from typing import Any

try:
    import mcp as _mcp
except ImportError as exc:
    raise ImportError(
        "cantus.adapters.mcp requires the mcp SDK. "
        "Run: pip install cantus[mcp]"
    ) from exc

# Re-export McpServer so `from cantus.adapters.mcp import McpServer`
# works when the SDK is installed.
from cantus.adapters.mcp_server import McpServer  # noqa: E402


def _start_server(
    *,
    name: str,
    version: str,
    tools: list[dict[str, Any]],
    skills: list[Any],
    transport: str,
    host: str,
    port: int,
) -> None:
    """Bridge to the mcp SDK Server lifecycle (blocking).

    The cantus.adapters.mcp_server.McpServer.run() entry calls this with
    its validated transport / host / port and the pre-built tool dict
    list. This function attaches each tool to a fresh mcp SDK Server
    instance and starts the requested transport loop.
    """
    # Lazy attribute access into the SDK so callers see ImportError-like
    # messages immediately if the SDK shape drifts.
    server_module = getattr(_mcp, "server", _mcp)
    Server = getattr(server_module, "Server", None)
    if Server is None:
        raise RuntimeError(
            "mcp SDK present but missing the expected `mcp.server.Server` "
            "entry point; pin a compatible version via `pip install "
            "'cantus[mcp]'` and check the SDK changelog."
        )

    server = Server(name=name, version=version)

    def _make_wrapper(sk: Any) -> Any:
        def _wrapped(**kwargs: Any) -> Any:
            return sk(**kwargs)
        return _wrapped

    for tool, sk in zip(tools, skills, strict=True):
        # SDK 1.x style: `Server.tool()` decorator binds a callable. The
        # cantus Skill is captured in a fresh closure per tool so each
        # tool dispatches to its own backing Skill.
        server.tool(
            name=tool["name"],
            description=tool["description"],
            inputSchema=tool["inputSchema"],
        )(_make_wrapper(sk))

    if transport == "stdio":
        stdio_module = getattr(server_module, "stdio", None)
        if stdio_module is None:
            raise RuntimeError(
                "mcp SDK missing `mcp.server.stdio` transport entry point"
            )
        stdio_server = getattr(stdio_module, "stdio_server", None)
        if stdio_server is None:
            raise RuntimeError(
                "mcp SDK missing `mcp.server.stdio.stdio_server` callable"
            )
        stdio_server(server)
    else:  # transport == "http"
        http_module = getattr(server_module, "streamable_http", None)
        if http_module is None:
            raise RuntimeError(
                "mcp SDK missing `mcp.server.streamable_http` transport entry point"
            )
        http_server = getattr(http_module, "streamable_http_server", None)
        if http_server is None:
            raise RuntimeError(
                "mcp SDK missing `mcp.server.streamable_http.streamable_http_server` callable"
            )
        http_server(server, host=host, port=port)


def _mcp_list_tools(
    *,
    transport: str,
    command_or_url: str,
) -> list[dict[str, Any]]:
    """Connect to a remote MCP server and return its `tools/list` response.

    Tests monkeypatch ``cantus.adapters.mcp_client._connect_and_list_mcp_tools``
    to inject fake tool dicts without exercising this SDK call. Production
    paths reach this function only when the ``mcp`` SDK is installed (the
    module-level import at the top of this file would have raised otherwise).
    """
    client_module = getattr(_mcp, "client", None)
    if client_module is None:
        raise RuntimeError(
            "mcp SDK present but missing the expected `mcp.client` entry point; "
            "pin a compatible version via `pip install 'cantus[mcp]'`."
        )
    list_tools = getattr(client_module, "list_tools", None)
    if list_tools is None:
        raise RuntimeError(
            "mcp SDK missing `mcp.client.list_tools` entry point"
        )
    return list(list_tools(transport=transport, command_or_url=command_or_url))


def _mcp_call_tool(
    *,
    transport: str,
    command_or_url: str,
    tool_name: str,
    args: dict[str, Any],
) -> Any:
    """Dispatch a single remote `tools/call` against an MCP server.

    Tests monkeypatch ``cantus.adapters.mcp_client._call_remote_tool``;
    production callers reach this function when the SDK is installed.
    """
    client_module = getattr(_mcp, "client", None)
    if client_module is None:
        raise RuntimeError(
            "mcp SDK present but missing the expected `mcp.client` entry point"
        )
    call_tool = getattr(client_module, "call_tool", None)
    if call_tool is None:
        raise RuntimeError(
            "mcp SDK missing `mcp.client.call_tool` entry point"
        )
    return call_tool(
        transport=transport,
        command_or_url=command_or_url,
        tool_name=tool_name,
        args=args,
    )


__all__ = ["McpServer", "_start_server", "_mcp_list_tools", "_mcp_call_tool"]
