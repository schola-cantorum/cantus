"""@debug stacking on protocols emits stdout trace."""

import io
import sys

from cantus.protocols.debug import debug
from cantus.protocols.skill import skill


def test_debug_skill_emits_trace_on_call(capsys):
    @debug
    @skill
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


def test_debug_rejects_non_protocol():
    import pytest

    with pytest.raises(TypeError):
        debug(lambda x: x)


def test_default_silent_run(capsys):
    """When @debug is NOT used, no framework output goes to stdout."""

    @skill
    def quiet_skill(x: int) -> int:
        """Quiet."""
        return x + 1

    quiet_skill(5)
    captured = capsys.readouterr()
    assert captured.out == ""
