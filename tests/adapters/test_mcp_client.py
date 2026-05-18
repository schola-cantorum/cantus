"""MCP client adapter — wraps remote MCP tools as cantus Skills."""

from __future__ import annotations

import pytest

from cantus.adapters.mcp_client import import_mcp_server
from cantus.protocols.skill import Skill

_SAMPLE_TOOLS = [
    {
        "name": "search",
        "description": "Search the catalog.",
        "inputSchema": {
            "type": "object",
            "properties": {"q": {"type": "string"}},
            "required": ["q"],
        },
    },
    {
        "name": "fetch",
        "description": "Fetch a record by id.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
]


@pytest.fixture
def mock_mcp(monkeypatch):
    """Replace the SDK gate so client tests can run without the mcp package."""

    def fake_list(transport, command_or_url):
        if "malformed" in command_or_url:
            raise RuntimeError("invalid protocol bytes")
        return list(_SAMPLE_TOOLS)

    def fake_call(transport, command_or_url, tool_name, args):
        if "broken" in command_or_url or tool_name == "broken_tool":
            raise RuntimeError("remote server returned error: -32603")
        return {"echoed_tool": tool_name, "echoed_args": args}

    monkeypatch.setattr(
        "cantus.adapters.mcp_client._connect_and_list_mcp_tools",
        fake_list,
    )
    monkeypatch.setattr(
        "cantus.adapters.mcp_client._call_remote_tool",
        fake_call,
    )
    return _SAMPLE_TOOLS


def test_import_returns_v030_shaped_skills(mock_mcp):
    skills = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")
    assert len(skills) == 2
    assert all(isinstance(s, Skill) for s in skills)
    for s, expected in zip(skills, mock_mcp, strict=True):
        spec = s.spec_for_llm()
        assert set(spec.keys()) == {"name", "description", "args_schema"}
        assert spec["name"] == expected["name"]


def test_imported_skill_args_schema_from_input_schema(mock_mcp):
    skills = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")
    for s, expected in zip(skills, mock_mcp, strict=True):
        spec = s.spec_for_llm()
        assert spec["args_schema"] == expected["inputSchema"]


def test_handshake_failure_raises_runtime_error(mock_mcp):
    with pytest.raises(RuntimeError, match="mcp_handshake_failed"):
        import_mcp_server(transport="stdio", command_or_url="malformed-server")


def test_remote_call_error_wraps_as_tool_error_observation(mock_mcp):
    """The imported Skill raises RuntimeError with "mcp_remote_error";
    cantus Agent dispatcher then wraps that into ToolErrorObservation
    automatically (see core.agent._dispatch_skill). The unit test here
    verifies the marker substring on the raise."""
    skills = import_mcp_server(transport="stdio", command_or_url="broken-server")
    with pytest.raises(RuntimeError, match="mcp_remote_error"):
        skills[0](q="anything")


def test_rejects_shell_metacharacter_command():
    for bad in (
        "echo-mcp; rm -rf /",
        "cat | bash",
        "server $(whoami)",
        "server `whoami`",
        "server > /tmp/out",
        "server < /etc/shadow",
        "server & background",
        "server\nrm -rf /",
    ):
        with pytest.raises(ValueError, match="command must be a binary path"):
            import_mcp_server(transport="stdio", command_or_url=bad)


def test_rejects_non_http_url():
    for bad in (
        "not-a-url",
        "ftp://example.com/mcp",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://",  # empty netloc
    ):
        with pytest.raises(ValueError, match=r"command_or_url must be http\(s\) URL"):
            import_mcp_server(transport="http", command_or_url=bad)


def test_imported_skill_has_is_remote_attribute(mock_mcp):
    skills = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")
    assert all(s.is_remote is True for s in skills)
    # Local class-first Skill stays False.

    class _LocalSkill(Skill):
        name = "local"
        description = "local skill."

        def run(self, x: str) -> str:
            return x

    assert _LocalSkill().is_remote is False
    # `is_remote` MUST NOT leak into spec_for_llm output (v0.3.0 shape contract).
    for s in skills:
        spec = s.spec_for_llm()
        assert "is_remote" not in spec
