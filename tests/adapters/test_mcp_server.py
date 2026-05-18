"""MCP server adapter — wraps cantus Skills as MCP tool definitions."""

from __future__ import annotations

import socket
import sys

import pytest

from cantus.adapters.mcp_server import export_as_mcp_server
from cantus.protocols.skill import Skill


class _SearchBookSkill(Skill):
    name = "search_book"
    description = "Search the library catalog by title."

    def run(self, title: str) -> str:
        return title


class _CheckAvailabilitySkill(Skill):
    name = "check_availability"
    description = "Check whether a book is in stock."

    def run(self, book_id: str) -> bool:
        return True


def test_export_preserves_spec_for_llm_shape():
    s1 = _SearchBookSkill()
    s2 = _CheckAvailabilitySkill()
    srv = export_as_mcp_server([s1, s2], name="cantus-demo", version="0.3.2")

    tools = srv.tools
    assert len(tools) == 2
    for raw, expected in zip(tools, (s1, s2), strict=True):
        spec = expected.spec_for_llm()
        assert raw["name"] == spec["name"]
        assert raw["description"] == spec["description"]
        assert raw["inputSchema"] == spec["args_schema"]


def test_export_rejects_empty_list():
    with pytest.raises(ValueError, match="requires at least one Skill"):
        export_as_mcp_server([], name="x", version="0.0.1")


def test_export_rejects_non_skill():
    with pytest.raises(TypeError, match=r"expects list\[Skill\]"):
        export_as_mcp_server(
            [{"name": "fake_skill"}],  # type: ignore[list-item]
            name="x",
            version="0.0.1",
        )


def test_run_rejects_unsupported_transport():
    srv = export_as_mcp_server([_SearchBookSkill()], name="x", version="0.0.1")
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
            [_SearchBookSkill()],
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
        srv = export_as_mcp_server([_SearchBookSkill()], name="x", version="0.0.1")
        with pytest.raises(OSError, match="Address already in use"):
            srv.run(transport="http", host="127.0.0.1", port=port)
    finally:
        blocker.close()
