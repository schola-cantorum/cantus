"""MCP server adapter — wraps cantus Tools as MCP tool definitions."""

from __future__ import annotations

import socket
import sys
import warnings

import pytest

from cantus.adapters.mcp_server import McpServer, export_as_mcp_server
from cantus.protocols.tool import Tool


class _SearchBookTool(Tool):
    name = "search_book"
    description = "Search the library catalog by title."

    def run(self, title: str) -> str:
        return title


class _CheckAvailabilityTool(Tool):
    name = "check_availability"
    description = "Check whether a book is in stock."

    def run(self, book_id: str) -> bool:
        return True


def test_export_preserves_spec_for_llm_shape():
    t1 = _SearchBookTool()
    t2 = _CheckAvailabilityTool()
    srv = export_as_mcp_server([t1, t2], name="cantus-demo", version="0.3.2")

    tools = srv.tools
    assert len(tools) == 2
    for raw, expected in zip(tools, (t1, t2), strict=True):
        spec = expected.spec_for_llm()
        assert raw["name"] == spec["name"]
        assert raw["description"] == spec["description"]
        assert raw["inputSchema"] == spec["args_schema"]


_EMPTY_MESSAGE = "export_as_mcp_server requires at least one Tool in the input list"

_EXPECTED_TOOLS = [
    {
        "name": "search_book",
        "description": "Search the library catalog by title.",
        "inputSchema": {
            "properties": {"title": {"title": "Title", "type": "string"}},
            "required": ["title"],
            "title": "SearchBookArgs",
            "type": "object",
        },
    },
    {
        "name": "check_availability",
        "description": "Check whether a book is in stock.",
        "inputSchema": {
            "properties": {"book_id": {"title": "Book Id", "type": "string"}},
            "required": ["book_id"],
            "title": "CheckAvailabilityArgs",
            "type": "object",
        },
    },
]


def test_export_tools_match_literal_for_positional_and_keyword():
    t1 = _SearchBookTool()
    t2 = _CheckAvailabilityTool()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        positional = export_as_mcp_server([t1, t2], name="demo", version="1.0")
        by_keyword = export_as_mcp_server(tools=[t1, t2], name="demo", version="1.0")
    assert positional.tools == _EXPECTED_TOOLS
    assert by_keyword.tools == _EXPECTED_TOOLS


def test_export_through_package_function_matches_literal():
    import cantus.adapters as adapters

    t1 = _SearchBookTool()
    t2 = _CheckAvailabilityTool()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        srv = adapters.export_as_mcp_server(tools=[t1, t2], name="demo", version="1.0")
    assert srv.tools == _EXPECTED_TOOLS


def test_mcp_server_class_accepts_any_iterable_of_tools():
    t1 = _SearchBookTool()
    t2 = _CheckAvailabilityTool()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        servers = [
            McpServer([t1, t2], name="demo", version="1.0"),
            McpServer(tools=[t1, t2], name="demo", version="1.0"),
            McpServer((t1, t2), name="demo", version="1.0"),
            McpServer(iter([t1, t2]), name="demo", version="1.0"),
        ]
    for server in servers:
        assert server.tools == _EXPECTED_TOOLS
    assert McpServer([], name="demo", version="1.0").tools == []


def test_mcp_server_class_requires_tools():
    with pytest.raises(TypeError, match=r"McpServer expects list\[Tool\], got NoneType"):
        McpServer(name="demo", version="1.0")
    with pytest.raises(TypeError, match=r"McpServer expects list\[Tool\], got NoneType"):
        McpServer(None, name="demo", version="1.0")


def test_export_rejects_empty_list():
    with pytest.raises(ValueError) as excinfo:
        export_as_mcp_server([], name="x", version="0.0.1")
    assert str(excinfo.value) == _EMPTY_MESSAGE


def test_export_rejects_anything_but_a_nonempty_list():
    a_tool = _SearchBookTool()
    for bad in ((a_tool,), (), iter([a_tool]), a_tool, None, "ab"):
        with pytest.raises(ValueError) as excinfo:
            export_as_mcp_server(bad, name="x", version="0.0.1")  # type: ignore[arg-type]
        assert str(excinfo.value) == _EMPTY_MESSAGE
    with pytest.raises(ValueError) as excinfo:
        export_as_mcp_server(name="x", version="0.0.1")
    assert str(excinfo.value) == _EMPTY_MESSAGE


def test_export_rejects_non_tool():
    with pytest.raises(TypeError, match=r"expects list\[Tool\]"):
        export_as_mcp_server(
            [{"name": "fake_tool"}],  # type: ignore[list-item]
            name="x",
            version="0.0.1",
        )


def test_non_tool_element_first_or_last_names_its_type():
    a_tool = _SearchBookTool()
    bad = {"name": "fake_tool"}
    for items in ([bad, a_tool], [a_tool, bad]):
        with pytest.raises(
            TypeError,
            match=r"export_as_mcp_server expects list\[Tool\], got element of type dict",
        ):
            export_as_mcp_server(items, name="x", version="0.0.1")  # type: ignore[arg-type]
        with pytest.raises(
            TypeError, match=r"McpServer expects list\[Tool\], got element of type dict"
        ):
            McpServer(items, name="x", version="0.0.1")  # type: ignore[arg-type]


def test_bad_name_or_version_wins_over_empty_list():
    with pytest.raises(ValueError, match="name must be alphanumeric"):
        export_as_mcp_server([], name="../x", version="1")
    with pytest.raises(ValueError, match="version must be alphanumeric"):
        export_as_mcp_server([], name="x", version="")


def test_run_rejects_unsupported_transport():
    srv = export_as_mcp_server([_SearchBookTool()], name="x", version="0.0.1")
    with pytest.raises(ValueError, match="transport must be 'stdio' or 'http'"):
        srv.run(transport="sse")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="transport must be 'stdio' or 'http'"):
        srv.run(transport="websocket")  # type: ignore[arg-type]


def test_import_without_mcp_sdk_raises_actionable_error(monkeypatch):
    """Simulate the no-SDK environment by hiding mcp from sys.modules."""
    for mod_name in list(sys.modules.keys()):
        if mod_name == "cantus.adapters.mcp" or mod_name.startswith("cantus.adapters.mcp."):
            del sys.modules[mod_name]
        if mod_name == "mcp" or mod_name.startswith("mcp."):
            del sys.modules[mod_name]
    monkeypatch.setitem(sys.modules, "mcp", None)

    with pytest.raises(ImportError, match=r"pip install cantus\[mcp\]"):
        from cantus.adapters.mcp import McpServer  # noqa: F401


@pytest.mark.parametrize(
    "name, version, offender",
    [
        ("../../malicious", "0.0.1", "name"),
        ("x\ny", "0.0.1", "name"),
        ("demo", "1.0\"}", "version"),
        ("x" * 65, "0.0.1", "name"),
        ("", "0.0.1", "name"),
        ("demo", "", "version"),
        (".leading_dot", "0.0.1", "name"),
        ("demo", "1.0 spaces", "version"),
    ],
)
def test_export_rejects_invalid_name_or_version(name, version, offender):
    with pytest.raises(ValueError, match=f"{offender} must be alphanumeric"):
        export_as_mcp_server(
            [_SearchBookTool()],
            name=name,
            version=version,
        )


def test_run_raises_address_in_use_when_port_busy():
    """Pre-bind a socket to an ephemeral port, then McpServer.run must fail loud."""
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    blocker.bind(("127.0.0.1", 0))
    port = blocker.getsockname()[1]
    try:
        srv = export_as_mcp_server([_SearchBookTool()], name="x", version="0.0.1")
        with pytest.raises(OSError, match="Address already in use"):
            srv.run(transport="http", host="127.0.0.1", port=port)
    finally:
        blocker.close()
