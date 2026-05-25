"""Settings override precedence — CLI > env > Settings default.

Covers Requirement「Settings override precedence is CLI args, then env vars,
then Settings defaults」 — the precedence resolution table in spec.md
maps row-by-row to a parameterised test.
"""

from __future__ import annotations

import pytest

from cantus.cli import _apply_override, main
from cantus.config import Settings


def _no_op_serve_capturing_settings(captured: dict):
    def fake_serve(registry, *, channels=None, settings=None):
        captured["settings"] = settings
        return object()

    return fake_serve


def _no_op_uvicorn_run(*args, **kwargs):
    return None


@pytest.mark.parametrize(
    "cli_host, env_host, expected_host",
    [
        ("1.2.3.4", "0.0.0.0", "1.2.3.4"),  # CLI overrides env
        ("1.2.3.4", None, "1.2.3.4"),  # CLI overrides default
        (None, "0.0.0.0", "0.0.0.0"),  # env overrides default
        (None, None, "127.0.0.1"),  # default
    ],
)
def test_host_precedence(monkeypatch, cli_host, env_host, expected_host):
    """Precedence table from spec — one parametrised case per row."""
    captured: dict = {}
    if env_host is None:
        monkeypatch.delenv("CANTUS_SERVE_HOST", raising=False)
    else:
        monkeypatch.setenv("CANTUS_SERVE_HOST", env_host)
    import cantus.serve
    import uvicorn

    monkeypatch.setattr(cantus.serve, "serve", _no_op_serve_capturing_settings(captured))
    monkeypatch.setattr(uvicorn, "run", _no_op_uvicorn_run)

    argv = [
        "serve",
        "--registry-import",
        "tests.cli.fixture_registry:registry",
    ]
    if cli_host is not None:
        argv += ["--host", cli_host]

    rc = main(argv)
    assert rc == 0
    assert captured["settings"].host == expected_host


def test_apply_override_skips_when_cli_unset():
    """`_apply_override` does NOT touch settings when args has the value None."""

    class _Args:
        host = None

    settings = Settings()
    settings.host = "from-env-or-default"
    _apply_override(settings, _Args(), "host", "host")
    assert settings.host == "from-env-or-default"


def test_apply_override_sets_when_cli_provided():
    """`_apply_override` overwrites settings when args has a non-None value."""

    class _Args:
        host = "from-cli"

    settings = Settings()
    settings.host = "from-env-or-default"
    _apply_override(settings, _Args(), "host", "host")
    assert settings.host == "from-cli"
