"""Tests for cantus.config (v0.4.0 cantus-serve-core).

Each test corresponds to one scenario from the
`cantus.config provides 12-factor settings via pydantic-settings`
Requirement in the cantus-serve-core capability.
"""

from __future__ import annotations

import importlib
from typing import Any
from collections.abc import Iterator
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _clear_cantus_serve_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip any pre-existing CANTUS_SERVE_* env so each test starts clean."""
    import os

    for key in list(os.environ):
        if key.startswith("CANTUS_SERVE_"):
            monkeypatch.delenv(key, raising=False)
    yield


def _load_settings_class() -> type[Any]:
    module = importlib.import_module("cantus.config")
    importlib.reload(module)
    return module.Settings


# --- Default-value scenario -----------------------------------------------


def test_defaults_match_declared_values() -> None:
    Settings = _load_settings_class()
    s = Settings()
    assert s.host == "127.0.0.1"
    assert s.port == 8765
    assert s.dashboard is True
    assert s.docs_url == "/docs"
    assert s.openapi_url == "/openapi.json"
    assert s.redoc_url == "/redoc"


# --- Env-prefix coercion scenarios ----------------------------------------


def test_port_env_coerces_string_to_int(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANTUS_SERVE_PORT", "9999")
    Settings = _load_settings_class()
    s = Settings()
    assert s.port == 9999
    assert isinstance(s.port, int)


def test_dashboard_env_coerces_string_to_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANTUS_SERVE_DASHBOARD", "false")
    Settings = _load_settings_class()
    s = Settings()
    assert s.dashboard is False


def test_host_env_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANTUS_SERVE_HOST", "0.0.0.0")
    Settings = _load_settings_class()
    s = Settings()
    assert s.host == "0.0.0.0"


def test_docs_url_env_accepts_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANTUS_SERVE_DOCS_URL", "")
    Settings = _load_settings_class()
    s = Settings()
    assert s.docs_url == ""


def test_env_overrides_compose_without_clobbering_unset_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CANTUS_SERVE_PORT", "9999")
    monkeypatch.setenv("CANTUS_SERVE_DASHBOARD", "false")
    Settings = _load_settings_class()
    s = Settings()
    assert s.port == 9999
    assert s.dashboard is False
    # Unset fields keep their declared defaults.
    assert s.host == "127.0.0.1"
    assert s.docs_url == "/docs"


# --- env_file behaviour scenario ------------------------------------------


def test_dotenv_file_is_not_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """v0.4.0 intentionally does NOT enable env_file. A .env in cwd must
    not influence Settings (deferred to cantus-serve-security)."""
    import os

    dotenv = tmp_path / ".env"
    dotenv.write_text("CANTUS_SERVE_PORT=12345\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CANTUS_SERVE_PORT", raising=False)

    Settings = _load_settings_class()
    s = Settings()
    # Default — .env file ignored.
    assert s.port == 8765
    # And the .env file is not introspected as part of model_config.
    cfg = getattr(Settings, "model_config", {})
    assert cfg.get("env_file") in (None, ""), (
        "Settings.model_config must not enable env_file in v0.4.0"
    )


# --- env_prefix metadata scenario -----------------------------------------


def test_settings_uses_cantus_serve_env_prefix() -> None:
    Settings = _load_settings_class()
    cfg = getattr(Settings, "model_config", {})
    assert cfg.get("env_prefix") == "CANTUS_SERVE_", (
        f"Settings.model_config.env_prefix must be 'CANTUS_SERVE_'; got: {cfg.get('env_prefix')!r}"
    )
