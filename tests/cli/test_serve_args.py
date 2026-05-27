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


# ---------- M1 (gate-a-audit-hardening): unsafe-default startup WARNING ------


def _no_op_uvicorn_run(*args, **kwargs):
    return None


def test_unsafe_default_combination_prints_stderr_warning(monkeypatch, capsys):
    """Default `auth-mode=none` + `dashboard=on` prints stderr WARNING.

    Task 6.1 / Scenario: default settings combination prints the WARNING.
    """
    import uvicorn

    from cantus.cli import main

    monkeypatch.delenv("CANTUS_SERVE_AUTH_MODE", raising=False)
    monkeypatch.delenv("CANTUS_SERVE_DASHBOARD", raising=False)
    monkeypatch.delenv("CANTUS_SERVE_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("CANTUS_SERVE_API_KEY", raising=False)
    monkeypatch.setattr(uvicorn, "run", _no_op_uvicorn_run)

    rc = main(
        [
            "serve",
            "--registry-import",
            "tests.cli.fixture_registry:registry",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "cantus serve: WARNING: auth-mode=none AND dashboard=on" in captured.err
    assert "cantus serve: WARNING:" not in captured.out


def test_unsafe_default_warning_absent_when_auth_set(monkeypatch, capsys):
    """`--auth-mode bearer` (with token env) suppresses the WARNING.

    Task 6.2 / Scenario: explicit --auth-mode bearer suppresses the WARNING.
    """
    import uvicorn

    from cantus.cli import main

    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "test-token")
    monkeypatch.setattr(uvicorn, "run", _no_op_uvicorn_run)

    rc = main(
        [
            "serve",
            "--registry-import",
            "tests.cli.fixture_registry:registry",
            "--auth-mode",
            "bearer",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "cantus serve: WARNING: auth-mode=none" not in captured.err


def test_unsafe_default_warning_absent_when_dashboard_off(monkeypatch, capsys):
    """`--no-dashboard` suppresses the WARNING even with auth=none.

    Task 6.2 / Scenario: explicit --no-dashboard suppresses the WARNING.
    """
    import uvicorn

    from cantus.cli import main

    monkeypatch.delenv("CANTUS_SERVE_AUTH_MODE", raising=False)
    monkeypatch.delenv("CANTUS_SERVE_BEARER_TOKEN", raising=False)
    monkeypatch.setattr(uvicorn, "run", _no_op_uvicorn_run)

    rc = main(
        [
            "serve",
            "--registry-import",
            "tests.cli.fixture_registry:registry",
            "--no-dashboard",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "cantus serve: WARNING: auth-mode=none AND dashboard=on" not in captured.err
