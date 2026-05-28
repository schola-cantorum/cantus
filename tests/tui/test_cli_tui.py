"""Tests for the `cantus tui` CLI subcommand wiring in cantus.cli."""

from __future__ import annotations

import builtins
from typing import Any

import pytest


def test_tui_help_lists_options(capsys: Any) -> None:
    from cantus.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main(["tui", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--url" in out
    assert "--auth-mode" in out
    assert "--poll-interval" in out


def test_tui_missing_extra_exits_nonzero_with_hint(
    monkeypatch: Any, capsys: Any
) -> None:
    from cantus.cli import main

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "textual":
            raise ImportError("simulated missing textual")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    rc = main(["tui", "--url", "http://127.0.0.1:8765"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cantus-agent[tui]" in err
    # No traceback leaked to stderr.
    assert "Traceback" not in err
