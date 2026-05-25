"""Argparse surface tests for `cantus serve`.

Covers Requirement「serve subcommand accepts host, port, registry-import,
auth-mode, dashboard, and channels arguments」 — help-text enumeration plus
missing-required + invalid-enum subprocess paths.
"""

from __future__ import annotations

import subprocess
import sys


def test_help_lists_all_seven_flags():
    """`cantus serve --help` stdout contains literal substrings for every flag.

    Scenario: help text enumerates all six args.
    """
    completed = subprocess.run(
        [sys.executable, "-m", "cantus", "serve", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    out = completed.stdout
    for needle in (
        "--host",
        "--port",
        "--registry-import",
        "--auth-mode",
        "--dashboard",
        "--no-dashboard",
        "--channels",
    ):
        assert needle in out, f"missing {needle!r} in serve --help stdout"


def test_missing_registry_import_exits_2():
    """`cantus serve` without `--registry-import` → argparse error → exit 2.

    Scenario: missing required --registry-import fails.
    """
    completed = subprocess.run(
        ["cantus", "serve"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "--registry-import" in completed.stderr


def test_invalid_auth_mode_exits_2():
    """`--auth-mode invalid-mode` rejected by argparse → exit 2 + enum listing.

    Scenario: --auth-mode rejects values outside the enum.
    """
    completed = subprocess.run(
        [
            "cantus",
            "serve",
            "--registry-import",
            "x:y",
            "--auth-mode",
            "invalid-mode",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    err = completed.stderr
    assert "none" in err
    assert "bearer" in err
    assert "api-key" in err
