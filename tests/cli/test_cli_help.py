"""Smoke tests for the `cantus` CLI entry point — in-process import path.

Covers Requirement「cantus ships a `cantus` console script and `python -m cantus`
entry point」for in-process import (`cantus.cli:main`). The subprocess-based
`cantus serve --help` byte-equivalence test for `python -m cantus serve --help`
lives in test_python_m_equivalence.py.

argparse's `--help` always raises `SystemExit(0)`; the integer return path of
`main()` is exercised by tests that run an actual subcommand body.
"""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout

import pytest

from cantus.cli import main


def test_help_text_starts_with_usage_cantus():
    """`cantus --help` stdout begins with `usage: cantus`.

    Scenario: console script invokes serve (the `--help` shape, exit 0).
    """
    out = io.StringIO()
    with redirect_stdout(out), pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    assert out.getvalue().startswith("usage: cantus")


def test_unknown_subcommand_exits_2():
    """Unknown subcommand → argparse error → exit 2.

    Scenario: unknown subcommand fails with argparse error.
    """
    err = io.StringIO()
    with redirect_stderr(err), pytest.raises(SystemExit) as excinfo:
        main(["unknown-subcommand"])
    assert excinfo.value.code == 2
    assert "unknown-subcommand" in err.getvalue()


def test_no_subcommand_exits_2():
    """`cantus` with no subcommand: subparser is required → argparse exits 2."""
    err = io.StringIO()
    with redirect_stderr(err), pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2
