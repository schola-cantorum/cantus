"""@debug stacking on protocols emits stdout trace."""

import warnings

import pytest

from cantus import Agent, CantusDeprecationWarning, Tool, tool
from cantus.core.observation import ToolObservation
from cantus.core.result import Result
from cantus.protocols.analyzer import analyzer
from cantus.protocols.debug import debug
from cantus.protocols.validator import validator
from tests.agent_helpers import ScriptedModel, call_json, final_json, tool_results

_DEBUG_TYPE_ERROR = (
    "@debug can only wrap a Tool or hook helper (Tool, Analyzer, Validator); "
    "got {t}. Make sure @debug is on top: `@debug` then `@tool`."
)


def _plain_function(x):
    return x


@pytest.mark.parametrize(
    "target, type_name",
    [
        (_plain_function, "function"),
        (42, "int"),
        (None, "NoneType"),
        (Tool, "type"),
    ],
)
def test_debug_rejects_non_protocol(target, type_name):
    with pytest.raises(TypeError) as excinfo:
        debug(target)
    assert str(excinfo.value) == _DEBUG_TYPE_ERROR.format(t=type_name)


def test_debug_wrong_decorator_order_raises():
    with pytest.raises(TypeError) as excinfo:

        @tool
        @debug
        def search_book(title: str) -> str:
            """Search."""
            return title

    assert str(excinfo.value) == _DEBUG_TYPE_ERROR.format(t="function")


def test_debug_tool_emits_trace_on_call(capsys):
    @debug
    @tool
    def search_book(title: str) -> str:
        """Search."""
        return f"found:{title}"

    out = search_book("Foundation")
    captured = capsys.readouterr()
    assert "[debug]" in captured.out
    assert "search_book" in captured.out
    assert "Foundation" in captured.out
    assert "found:Foundation" in captured.out
    assert out == "found:Foundation"


def test_default_silent_run(capsys):
    """When @debug is NOT used, no framework output goes to stdout."""

    @tool
    def quiet_tool(x: int) -> int:
        """Quiet."""
        return x + 1

    quiet_tool(5)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_debug_above_tool_traces_direct_call_and_agent_call(capsys):
    with warnings.catch_warnings():
        warnings.simplefilter("error", CantusDeprecationWarning)

        @debug
        @tool
        def search_book(title: str) -> str:
            """Search."""
            return f"found:{title}"

        assert isinstance(search_book, Tool)
        assert search_book("Foundation") == "found:Foundation"
        lines = capsys.readouterr().out.splitlines()
        assert "[debug] registered SearchBook 'search_book'" in lines
        assert any(line.startswith("[debug] spec=") for line in lines)
        assert (
            '[debug] search_book thought=\'\' args=["Foundation"]/{} result="found:Foundation"'
            in lines
        )

        model = ScriptedModel(
            [call_json("search_book", title="Foundation"), final_json()]
        )
        stream = Agent(model, tools=[search_book]).run("q").stream
        observed = [e for e in stream if isinstance(e, ToolObservation)]
        assert len(observed) == 1
        assert observed[0].result == "found:Foundation"
        lines = capsys.readouterr().out.splitlines()
        assert (
            '[debug] search_book thought=\'\' args=[]/{"title": "Foundation"} result="found:Foundation"'
            in lines
        )


def test_debug_wraps_class_first_tool_instance(capsys):
    with warnings.catch_warnings():
        warnings.simplefilter("error", CantusDeprecationWarning)

        class Echo(Tool):
            """Echo text back."""

            name = "echo"

            def run(self, text: str) -> str:
                return text

        instance = Echo()
        assert debug(instance) is instance
        capsys.readouterr()
        instance("hi")
        lines = capsys.readouterr().out.splitlines()
        assert any(line.startswith("[debug] echo ") for line in lines)


def test_debug_above_tool_with_pre_hook_runs_hook(capsys):
    with warnings.catch_warnings():
        warnings.simplefilter("error", CantusDeprecationWarning)

        def shout(text: str) -> dict:
            return {"text": text + "!"}

        @debug
        @tool(pre_hook=shout)
        def echo(text: str) -> str:
            """Echo."""
            return text

        assert isinstance(echo, Tool)
        capsys.readouterr()
        model = ScriptedModel([call_json("echo", text="hi"), final_json()])
        stream = Agent(model, tools=[echo]).run("q").stream
        assert tool_results(stream) == [("echo", "hi!")]
        out = capsys.readouterr().out
        assert '[debug] echo thought=\'\' args=[]/{"text": "hi!"} result="hi!"' in out.splitlines()
        # the tool is traced, its plain hook is not: no hook label
        assert "invoked from" not in out


def test_debug_pre_hook_label_precedes_hook_trace(capsys):
    @debug
    @analyzer
    def parse_location(text: str) -> str:
        """Upper-case the location."""
        return text.upper()

    @tool(pre_hook=parse_location)
    def get_weather(text: str) -> str:
        """Weather."""
        return f"weather@{text}"

    capsys.readouterr()
    model = ScriptedModel([call_json("get_weather", text="tainan"), final_json()])
    stream = Agent(model, tools=[get_weather]).run("q").stream
    lines = capsys.readouterr().out.splitlines()
    label = "[debug] pre_hook 'parse_location' invoked from tool 'get_weather'"
    own = '[debug] parse_location thought=\'\' args=[]/{"text": "tainan"} result="TAINAN"'
    assert lines.count(label) == 1
    assert lines.index(label) < lines.index(own)
    assert tool_results(stream) == [("get_weather", "weather@TAINAN")]


def test_debug_post_hook_label_precedes_hook_trace(capsys):
    @debug
    @validator
    def non_empty(value: str) -> Result:
        """Reject empty text."""
        return Result.success(value)

    @tool(post_hook=non_empty)
    def echo(text: str) -> str:
        """Echo."""
        return text

    capsys.readouterr()
    model = ScriptedModel([call_json("echo", text="hi"), final_json()])
    stream = Agent(model, tools=[echo]).run("q").stream
    lines = capsys.readouterr().out.splitlines()
    label = "[debug] post_hook 'non_empty' invoked from tool 'echo'"
    assert lines.count(label) == 1
    own_index = next(
        i for i, line in enumerate(lines) if line.startswith("[debug] non_empty thought=")
    )
    assert lines.index(label) < own_index
    assert len([e for e in stream if isinstance(e, ToolObservation)]) == 1
    assert tool_results(stream) == [("echo", "hi")]


@pytest.mark.parametrize("role", ["pre_hook", "post_hook"])
def test_unwrapped_hook_prints_no_invoked_from_label(role, capsys):
    def upper(text):
        return {"text": text.upper()} if role == "pre_hook" else text.upper()

    @tool(**{role: upper})
    def echo(text: str) -> str:
        """Echo."""
        return text

    capsys.readouterr()
    model = ScriptedModel([call_json("echo", text="hi"), final_json()])
    stream = Agent(model, tools=[echo]).run("q").stream
    # the hook ran (it upper-cased the argument or the result) and printed no label
    assert tool_results(stream) == [("echo", "HI")]
    assert "invoked from" not in capsys.readouterr().out
