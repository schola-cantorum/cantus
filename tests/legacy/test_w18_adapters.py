"""W18 (the keywords skill= and skills= of the adapter entry points)."""

from __future__ import annotations

import sys
import warnings
from typing import Any

import pytest

import cantus
from cantus.protocols.tool import tool
from tests.adapters.test_dspy import _install_fake_dspy
from tests.adapters.test_huggingface import _install_fake_smolagents
from tests.adapters.test_langchain import _install_fake_langchain
from tests.adapters.test_openhands import _install_fake_openhands
from tests.legacy.support import (
    EXPECTED,
    cantus_records,
    import_module_from,
    run_python,
    write_module,
)

_ADAPTER_MODULES = ("langchain", "dspy", "huggingface", "openhands")

_ONE_AT_A_TIME = "pass either tool= or skill=, not both"
_LISTS_ONE_AT_A_TIME = "pass either tools= or skills=, not both"
_EMPTY_MESSAGE = "export_as_mcp_server requires at least one Tool in the input list"

_ALPHA_BETA = [
    {
        "name": "alpha",
        "description": "Alpha.",
        "inputSchema": {
            "properties": {"x": {"title": "X", "type": "string"}},
            "required": ["x"],
            "title": "AlphaArgs",
            "type": "object",
        },
    },
    {
        "name": "beta",
        "description": "Beta.",
        "inputSchema": {
            "properties": {"y": {"title": "Y", "type": "integer"}},
            "required": ["y"],
            "title": "BetaArgs",
            "type": "object",
        },
    },
]

_TOOLS_SOURCE = '''\
from cantus.protocols.tool import tool


@tool
def alpha(x: str) -> str:
    """Alpha."""
    return x


@tool
def beta(y: int) -> int:
    """Beta."""
    return y


'''


@pytest.fixture
def fake_sdks(monkeypatch):
    """Install the four fake SDKs; drop the adapter modules again afterwards."""
    _install_fake_langchain(monkeypatch)
    _install_fake_dspy(monkeypatch)
    _install_fake_smolagents(monkeypatch)
    _install_fake_openhands(monkeypatch)
    yield
    for name in _ADAPTER_MODULES:
        sys.modules.pop(f"cantus.adapters.{name}", None)


@pytest.fixture
def echo():
    @tool
    def echo(x: str) -> str:
        """Echo the text."""
        return f"echo:{x}"

    return echo


# --- the four expose_* functions: (public function name, module name) -----------

_EXPOSERS = [
    ("expose_as_langchain_tool", "langchain"),
    ("expose_as_dspy_tool", "dspy"),
    ("expose_as_hf_tool", "huggingface"),
    ("expose_as_openhands_action", "openhands"),
]
_EXPOSER_IDS = [fn_name for fn_name, _ in _EXPOSERS]


def _entry_points(fn_name: str, module_name: str) -> list[Any]:
    import importlib

    import cantus.adapters as adapters

    module = importlib.import_module(f"cantus.adapters.{module_name}")
    return [getattr(adapters, fn_name), getattr(module, fn_name)]


def _assert_converted(fn_name: str, converted: Any) -> None:
    """The converted object is usable and carries the literal results of ``echo``."""
    if fn_name == "expose_as_langchain_tool":
        assert converted.name == "echo"
        assert converted.invoke({"x": "a"}) == "echo:a"
    elif fn_name == "expose_as_dspy_tool":
        assert converted.name == "echo"
        assert converted(x="a") == "echo:a"
    elif fn_name == "expose_as_hf_tool":
        assert converted.name == "echo"
        assert converted(x="a") == "echo:a"
    else:
        assert converted.tool_name == "echo"
        assert converted.description == "Echo the text."
        assert converted.args_schema == {
            "properties": {"x": {"title": "X", "type": "string"}},
            "required": ["x"],
            "title": "EchoArgs",
            "type": "object",
        }


def _record(call):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = call()
    return result, cantus_records(caught)


@pytest.mark.parametrize("fn_name, module_name", _EXPOSERS, ids=_EXPOSER_IDS)
def test_skill_keyword_converts_and_warns_once(fake_sdks, echo, fn_name, module_name):  # row 16
    for fn in _entry_points(fn_name, module_name):
        for call in (lambda: fn(skill=echo), lambda: fn(None, skill=echo)):
            converted, records = _record(call)
            _assert_converted(fn_name, converted)
            assert len(records) == 1
            assert records[0].category is cantus.CantusDeprecationWarning
            assert str(records[0].message) == EXPECTED["W18:skill"]


_STUB_CALLER = '''\
import cantus.adapters
{tools}
converted = cantus.adapters.expose_as_langchain_tool(skill=alpha)
'''

_MODULE_CALLER = '''\
import cantus.adapters.openhands
{tools}
converted = cantus.adapters.openhands.expose_as_openhands_action(skill=alpha)
'''


@pytest.mark.parametrize(
    "name, source",
    [("w18_stub_caller", _STUB_CALLER), ("w18_module_caller", _MODULE_CALLER)],
    ids=["stub-path", "module-path"],
)
def test_skill_keyword_is_attributed_to_the_calling_line(
    fake_sdks, tmp_path, name, source
):  # row 17
    text = source.format(tools=_TOOLS_SOURCE)
    path = write_module(tmp_path, name, text)
    call_line = next(
        i for i, line in enumerate(text.splitlines(), 1) if line.startswith("converted =")
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import_module_from(tmp_path, name)
    records = cantus_records(caught)
    assert [str(w.message) for w in records] == [EXPECTED["W18:skill"]]
    assert records[0].category is cantus.CantusDeprecationWarning
    assert records[0].filename == str(path)
    assert records[0].lineno == call_line


_MCP_EXPORT_CALLER = '''\
from cantus.adapters import export_as_mcp_server
{tools}
server = export_as_mcp_server(skills=[alpha, beta], name="demo", version="1.0")
'''

_MCP_CLASS_CALLER = '''\
from cantus.adapters.mcp_server import McpServer
{tools}
server = McpServer(skills=[alpha, beta], name="demo", version="1.0")
'''


@pytest.mark.parametrize(
    "name, source",
    [("w18_export_caller", _MCP_EXPORT_CALLER), ("w18_class_caller", _MCP_CLASS_CALLER)],
    ids=["export_as_mcp_server", "McpServer"],
)
def test_skills_keyword_converts_and_is_attributed(tmp_path, name, source):  # row 18
    text = source.format(tools=_TOOLS_SOURCE)
    path = write_module(tmp_path, name, text)
    call_line = next(
        i for i, line in enumerate(text.splitlines(), 1) if line.startswith("server =")
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        module = import_module_from(tmp_path, name)
    records = cantus_records(caught)
    assert module.server.tools == _ALPHA_BETA
    assert [str(w.message) for w in records] == [EXPECTED["W18:skills"]]
    assert records[0].category is cantus.CantusDeprecationWarning
    assert records[0].filename == str(path)
    assert records[0].lineno == call_line


def _no_cantus_warning(call) -> Exception:
    """Run ``call`` expecting an exception; assert no cantus warning was recorded."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(Exception) as excinfo:
            call()
    assert cantus_records(caught) == []
    return excinfo.value


@pytest.fixture
def two_tools():
    @tool
    def alpha(x: str) -> str:
        """Alpha."""
        return x

    @tool
    def beta(y: int) -> int:
        """Beta."""
        return y

    return alpha, beta


@pytest.mark.parametrize("fn_name, module_name", _EXPOSERS, ids=_EXPOSER_IDS)
def test_both_keywords_raise_without_warning(fake_sdks, echo, fn_name, module_name):  # row 19
    for fn in _entry_points(fn_name, module_name):
        for call in (lambda: fn(tool=echo, skill=echo), lambda: fn(echo, skill=echo)):
            error = _no_cantus_warning(call)
            assert isinstance(error, TypeError)
            assert _ONE_AT_A_TIME in str(error)


def test_both_list_keywords_raise_without_warning(two_tools):  # row 19
    from cantus.adapters import export_as_mcp_server
    from cantus.adapters.mcp_server import McpServer

    alpha, _ = two_tools
    for call in (
        lambda: export_as_mcp_server([alpha], skills=[alpha], name="demo", version="1.0"),
        lambda: McpServer([alpha], skills=[alpha], name="demo", version="1.0"),
    ):
        error = _no_cantus_warning(call)
        assert isinstance(error, TypeError)
        assert _LISTS_ONE_AT_A_TIME in str(error)


@pytest.mark.parametrize("fn_name, module_name", _EXPOSERS, ids=_EXPOSER_IDS)
def test_wrong_skill_value_raises_without_warning(
    fake_sdks, echo, fn_name, module_name
):  # row 20
    for fn in _entry_points(fn_name, module_name):
        for call in (lambda: fn(skill=42), lambda: fn(echo, skill=42)):
            error = _no_cantus_warning(call)
            assert isinstance(error, TypeError)
            assert f"{fn_name} expects Tool, got int" in str(error)
        converted, records = _record(lambda: fn(echo, skill=None))
        _assert_converted(fn_name, converted)
        assert records == []


def test_wrong_skills_value_raises_without_warning(two_tools):  # row 20
    from cantus.adapters import export_as_mcp_server
    from cantus.adapters.mcp_server import McpServer

    alpha, _ = two_tools
    for call, label in (
        (
            lambda: export_as_mcp_server(skills=[alpha, 42], name="demo", version="1.0"),
            "export_as_mcp_server",
        ),
        (lambda: McpServer(skills=[alpha, 42], name="demo", version="1.0"), "McpServer"),
    ):
        error = _no_cantus_warning(call)
        assert isinstance(error, TypeError)
        assert f"{label} expects list[Tool], got element of type int" in str(error)

    for empty in ([], (alpha,)):
        error = _no_cantus_warning(
            lambda: export_as_mcp_server(skills=empty, name="demo", version="1.0")
        )
        assert isinstance(error, ValueError)
        assert str(error) == _EMPTY_MESSAGE

    error = _no_cantus_warning(
        lambda: export_as_mcp_server(skills=[alpha], name="../x", version="1")
    )
    assert isinstance(error, ValueError)
    assert "name must be alphanumeric" in str(error)


_SCRIPT = '''\
from cantus.adapters import export_as_mcp_server
from cantus.protocols.tool import tool


@tool
def t(x: str) -> str:
    """Echo."""
    return x


server = export_as_mcp_server({keyword}=[t], name="x", version="1")
print("converted", len(server.tools))
'''


def test_skills_keyword_prints_once_by_default(tmp_path):  # row 21
    write_module(tmp_path, "script", _SCRIPT.format(keyword="skills"))
    proc = run_python(["script.py"], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "converted 1" in proc.stdout
    assert proc.stderr.count(EXPECTED["W18:skills"]) == 1


def test_skills_keyword_fails_under_error_filter(tmp_path):  # row 21
    write_module(tmp_path, "script", _SCRIPT.format(keyword="skills"))
    proc = run_python(["-W", "error::DeprecationWarning", "script.py"], cwd=tmp_path)
    assert proc.returncode != 0
    assert "CantusDeprecationWarning" in proc.stderr


def test_tools_keyword_is_clean_under_error_filter(tmp_path):  # row 21
    write_module(tmp_path, "script", _SCRIPT.format(keyword="tools"))
    proc = run_python(["-W", "error::DeprecationWarning", "script.py"], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "deprecated since cantus" not in proc.stderr
