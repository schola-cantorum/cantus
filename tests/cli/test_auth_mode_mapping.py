"""Auth-mode kebab → AuthMode enum mapping tests.

Covers Requirement「--auth-mode maps kebab-case CLI values to AuthMode enum」.
The CLI accepts `none` / `bearer` / `api-key` and maps them to
`AuthMode.NONE` / `AuthMode.BEARER` / `AuthMode.API_KEY`. Uppercase enum names
are rejected by argparse with exit 2.
"""

from __future__ import annotations

import io
import subprocess
from contextlib import redirect_stderr

import pytest

from cantus.cli import _AUTH_MODE_BY_CLI_VALUE, main
from cantus.config import AuthMode, Settings


def test_mapping_table_matches_enum():
    """Dict literally maps `none` / `bearer` / `api-key` to enum members."""
    assert _AUTH_MODE_BY_CLI_VALUE == {
        "none": AuthMode.NONE,
        "bearer": AuthMode.BEARER,
        "api-key": AuthMode.API_KEY,
    }


def _no_op_serve_capturing_settings(captured: dict):
    """Build a `cantus.serve.serve` replacement that captures the Settings arg
    and returns a sentinel object that uvicorn.run can accept."""

    def fake_serve(registry, *, channels=None, settings=None):
        captured["registry"] = registry
        captured["channels"] = channels
        captured["settings"] = settings
        return object()

    return fake_serve


def _no_op_uvicorn_run(*args, **kwargs):
    return None


def test_bearer_kebab_maps_to_bearer_enum(monkeypatch):
    """`--auth-mode bearer` → Settings.auth_mode == AuthMode.BEARER.

    Scenario: kebab string maps to bearer enum.
    """
    captured: dict = {}
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "test-token")
    monkeypatch.setattr("cantus.cli._build_app", _no_op_serve_capturing_settings(captured), raising=False)
    # `_build_app` is imported inside `_cmd_serve`; patch the source.
    import cantus.serve

    monkeypatch.setattr(cantus.serve, "serve", _no_op_serve_capturing_settings(captured))
    import cantus.cli

    monkeypatch.setattr(cantus.cli, "_build_app", _no_op_serve_capturing_settings(captured), raising=False)
    # Final hook: uvicorn.run no-op so the test does not actually start a server.
    import uvicorn

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
    settings = captured["settings"]
    assert isinstance(settings, Settings)
    assert settings.auth_mode == AuthMode.BEARER


def test_api_key_kebab_maps_to_api_key_enum(monkeypatch):
    """`--auth-mode api-key` → Settings.auth_mode == AuthMode.API_KEY.

    Scenario: kebab string maps to api-key enum.
    """
    captured: dict = {}
    monkeypatch.setenv("CANTUS_SERVE_API_KEY", "test-key")
    import cantus.serve
    import uvicorn

    monkeypatch.setattr(cantus.serve, "serve", _no_op_serve_capturing_settings(captured))
    monkeypatch.setattr(uvicorn, "run", _no_op_uvicorn_run)

    rc = main(
        [
            "serve",
            "--registry-import",
            "tests.cli.fixture_registry:registry",
            "--auth-mode",
            "api-key",
        ]
    )
    assert rc == 0
    assert captured["settings"].auth_mode == AuthMode.API_KEY


def test_uppercase_enum_name_rejected(monkeypatch):
    """`--auth-mode BEARER` rejected by argparse → exit 2.

    Scenario: uppercase enum name is rejected.
    """
    err = io.StringIO()
    with redirect_stderr(err), pytest.raises(SystemExit) as excinfo:
        main(
            [
                "serve",
                "--registry-import",
                "tests.cli.fixture_registry:registry",
                "--auth-mode",
                "BEARER",
            ]
        )
    assert excinfo.value.code == 2
    err_text = err.getvalue()
    assert "none" in err_text
    assert "bearer" in err_text
    assert "api-key" in err_text


def test_uppercase_enum_name_rejected_subprocess():
    """Same as test_uppercase_enum_name_rejected but via subprocess for end-to-end
    coverage of the installed `cantus` console script."""
    completed = subprocess.run(
        [
            "cantus",
            "serve",
            "--registry-import",
            "tests.cli.fixture_registry:registry",
            "--auth-mode",
            "BEARER_TOKEN",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
