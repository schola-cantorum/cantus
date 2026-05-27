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


# --- v0.4.1 cantus-serve-security: AuthMode + SecretStr -------------------


def test_authmode_default_is_none_preserves_v040_zero_auth() -> None:
    """Defaulting to AuthMode.NONE keeps v0.4.0 zero-auth behavior."""
    from cantus.config import AuthMode

    Settings = _load_settings_class()
    s = Settings()
    assert s.auth_mode == AuthMode.NONE
    assert s.auth_mode.value == "none"
    assert s.api_key is None
    assert s.bearer_token is None
    assert s.dashboard_requires_auth is True


def test_authmode_env_coerces_string_to_enum(monkeypatch: pytest.MonkeyPatch) -> None:
    from cantus.config import AuthMode

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    Settings = _load_settings_class()
    s = Settings()
    assert s.auth_mode == AuthMode.BEARER
    assert s.auth_mode.value == "bearer"


def test_authmode_env_accepts_api_key_string(monkeypatch: pytest.MonkeyPatch) -> None:
    from cantus.config import AuthMode

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "api-key")
    Settings = _load_settings_class()
    s = Settings()
    assert s.auth_mode == AuthMode.API_KEY
    assert s.auth_mode.value == "api-key"


def test_bearer_token_env_wraps_in_secretstr(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import SecretStr

    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "correct-secret")
    Settings = _load_settings_class()
    s = Settings()
    assert isinstance(s.bearer_token, SecretStr)
    assert s.bearer_token.get_secret_value() == "correct-secret"
    # SecretStr masks in repr — must NOT contain the plaintext.
    assert "correct-secret" not in repr(s.bearer_token)
    assert "correct-secret" not in repr(s)


def test_api_key_env_wraps_in_secretstr(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import SecretStr

    monkeypatch.setenv("CANTUS_SERVE_API_KEY", "correct-key")
    Settings = _load_settings_class()
    s = Settings()
    assert isinstance(s.api_key, SecretStr)
    assert s.api_key.get_secret_value() == "correct-key"
    assert "correct-key" not in repr(s.api_key)
    assert "correct-key" not in repr(s)


def test_secretstr_fields_do_not_leak_in_model_dump_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "correct-secret")
    monkeypatch.setenv("CANTUS_SERVE_API_KEY", "correct-key")
    Settings = _load_settings_class()
    s = Settings()
    dumped = s.model_dump_json()
    assert "correct-secret" not in dumped
    assert "correct-key" not in dumped


def test_dashboard_requires_auth_env_coerces_to_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH", "false")
    Settings = _load_settings_class()
    s = Settings()
    assert s.dashboard_requires_auth is False


# --- v0.4.5 cantus-channel-gateway-webhook: SecretStr channel fields -----


def test_channel_secrets_default_to_none() -> None:
    Settings = _load_settings_class()
    s = Settings()
    assert s.channel_line_secret is None
    assert s.channel_line_access_token is None
    assert s.channel_telegram_secret_token is None
    assert s.channel_telegram_bot_token is None


def test_channel_line_secret_env_wraps_in_secretstr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import SecretStr

    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_LINE_SECRET", "s3cret-line")
    Settings = _load_settings_class()
    s = Settings()
    assert isinstance(s.channel_line_secret, SecretStr)
    assert s.channel_line_secret.get_secret_value() == "s3cret-line"
    assert "s3cret-line" not in repr(s.channel_line_secret)
    assert "s3cret-line" not in repr(s)


def test_channel_line_access_token_env_wraps_in_secretstr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import SecretStr

    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN", "tok-line")
    Settings = _load_settings_class()
    s = Settings()
    assert isinstance(s.channel_line_access_token, SecretStr)
    assert s.channel_line_access_token.get_secret_value() == "tok-line"
    assert "tok-line" not in repr(s)


def test_channel_telegram_secret_token_env_wraps_in_secretstr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import SecretStr

    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN", "tg-secret")
    Settings = _load_settings_class()
    s = Settings()
    assert isinstance(s.channel_telegram_secret_token, SecretStr)
    assert s.channel_telegram_secret_token.get_secret_value() == "tg-secret"
    assert "tg-secret" not in repr(s)


def test_channel_telegram_bot_token_env_wraps_in_secretstr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import SecretStr

    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN", "123:tg-bot")
    Settings = _load_settings_class()
    s = Settings()
    assert isinstance(s.channel_telegram_bot_token, SecretStr)
    assert s.channel_telegram_bot_token.get_secret_value() == "123:tg-bot"
    assert "123:tg-bot" not in repr(s)


def test_channel_secrets_do_not_leak_in_model_dump_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_LINE_SECRET", "leak-line-1")
    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN", "leak-line-2")
    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN", "leak-tg-1")
    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN", "leak-tg-2")
    Settings = _load_settings_class()
    s = Settings()
    dumped = s.model_dump_json()
    assert "leak-line-1" not in dumped
    assert "leak-line-2" not in dumped
    assert "leak-tg-1" not in dumped
    assert "leak-tg-2" not in dumped


def test_discord_fields_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.2 — Requirement: Settings adds three Discord channel fields with masked secrets.

    The three new fields populate from the same `CANTUS_SERVE_` env prefix
    used by line/telegram secrets. SecretStr-wrapped secrets keep their
    plaintext recoverable via `.get_secret_value()`; application_id stays
    plain str because it is a publicly-visible identifier.
    """
    from pydantic import SecretStr

    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN", "MTAxxx.discord.bot")
    monkeypatch.setenv(
        "CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY",
        "deadbeef" * 8,
    )
    monkeypatch.setenv(
        "CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID", "1234567890"
    )
    Settings = _load_settings_class()
    s = Settings()
    assert isinstance(s.channel_discord_bot_token, SecretStr)
    assert s.channel_discord_bot_token.get_secret_value() == "MTAxxx.discord.bot"
    assert isinstance(s.channel_discord_public_key, SecretStr)
    assert s.channel_discord_public_key.get_secret_value() == "deadbeef" * 8
    # application_id is a plain str — publicly visible identifier, not secret.
    assert s.channel_discord_application_id == "1234567890"
    assert isinstance(s.channel_discord_application_id, str)


def test_discord_fields_default_none() -> None:
    """Task 1.2 — Requirement: Settings adds three Discord channel fields with masked secrets.

    All three Discord channel fields default to None so existing v0.4.5
    deployments that never set CANTUS_SERVE_CHANNEL_DISCORD_* keep behaviour
    byte-identical.
    """
    Settings = _load_settings_class()
    s = Settings()
    assert s.channel_discord_bot_token is None
    assert s.channel_discord_public_key is None
    assert s.channel_discord_application_id is None


def test_discord_secrets_masked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.3 — Requirement: Settings adds three Discord channel fields with masked secrets.

    Verifies SecretStr discipline: the two secret fields never leak in
    `repr(settings)`, `model_dump_json()`, or the generated OpenAPI schema.
    `channel_discord_application_id` is NOT masked (public identifier).
    """
    import json

    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN", "leak-discord-bot")
    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY", "leak-discord-pk")
    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID", "public-app-id-001")
    Settings = _load_settings_class()
    s = Settings()
    # repr never shows the secret plaintext.
    assert "leak-discord-bot" not in repr(s)
    assert "leak-discord-pk" not in repr(s)
    # application_id is public — DOES appear in repr.
    assert "public-app-id-001" in repr(s)
    # model_dump_json masks SecretStr, preserves application_id plaintext.
    dumped = s.model_dump_json()
    assert "leak-discord-bot" not in dumped
    assert "leak-discord-pk" not in dumped
    assert "public-app-id-001" in dumped
    # OpenAPI schema does not expose either secret value or the field names.
    from cantus.core.registry import Registry
    from cantus.serve import serve

    app = serve(Registry(), settings=Settings())
    schema_json = json.dumps(app.openapi())
    assert "leak-discord-bot" not in schema_json
    assert "leak-discord-pk" not in schema_json
    assert "channel_discord_bot_token" not in schema_json
    assert "channel_discord_public_key" not in schema_json


def test_channel_secrets_absent_from_openapi(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.2: SecretStr channel fields must NOT appear in the FastAPI
    OpenAPI schema. cantus.serve.app does not bind Settings into a request
    body, so an empty/scan-clean OpenAPI components.schemas plus an absence
    of the env var names anywhere in the JSON is the contract."""
    import json

    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_LINE_SECRET", "openapi-leak-test-A")
    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN", "openapi-leak-test-B")
    Settings = _load_settings_class()

    from cantus.core.registry import Registry
    from cantus.serve import serve

    app = serve(Registry(), settings=Settings())
    schema_json = json.dumps(app.openapi())
    assert "openapi-leak-test-A" not in schema_json
    assert "openapi-leak-test-B" not in schema_json
    # Field names also absent — Settings is not exposed.
    assert "channel_line_secret" not in schema_json
    assert "channel_telegram_bot_token" not in schema_json
